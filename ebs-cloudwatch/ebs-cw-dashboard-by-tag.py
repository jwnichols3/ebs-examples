import boto3
import argparse
import json
import logging
import sys
import collections


class Config:
    PAGINATION_COUNT = 300  # Set the number of items per page
    DASHBOARD_METRICS_LIMIT = 2500  # Set the number of metrics per dashboard.


def main():
    args = parse_args()

    initialize_logging(args.loglevel)

    ec2_client, cloudwatch = initialize_aws_clients(region=args.region)

    ebs_volume_information = get_ebs_volume_information(ec2_client=ec2_client)

    if args.list_tags or args.tag_name is None:
        if args.list_tags:
            if args.verbose:
                print("EBS Volumes:")
                print(ebs_volume_information)
            list_unique_tag_names(ebs_volumes=ebs_volume_information)
            sys.exit(0)

        if args.tag_name is None:
            print("No tag name provided. Here are the available tag names:")
            list_unique_tag_names(ebs_volumes=ebs_volume_information)
            sys.exit(0)

    volumes_by_tag = filter_volumes_by_tag(ebs_volume_information, args.tag_name)

    current_dashboards = list_existing_dashboards(cloudwatch, args.tag_name)

    new_dashboards = construct_dashboard(
        cloudwatch=cloudwatch,
        tag_name=args.tag_name,
        region=args.region,
        verbose=args.verbose,
        dry_run=args.dry_run,
        volumes_by_tag=volumes_by_tag,
        ebs_volume_information=ebs_volume_information,
    )

    if not args.no_cleanup:
        if args.verbose:
            print("\n=== Dashboard Cleanup ===")
            print("\nPrevious dashboards:")
            print("\n".join(current_dashboards))
            print("\nNew dashboards:")
            print("\n".join(new_dashboards))

        dashboard_cleanup(
            cloudwatch=cloudwatch,
            current_dashboards=current_dashboards,
            new_dashboards=new_dashboards,
        )


def construct_dashboard(
    cloudwatch,
    region,
    tag_name=None,
    verbose=False,
    dry_run=False,
    volumes_by_tag=[],
    ebs_volume_information=[],
):
    new_dashboards = []
    dashboard_name = ""

    for tag_value, volumes in volumes_by_tag.items():
        current_metric_count = 0
        current_dashboard_number = 1
        widgets = []

        for i, volume in enumerate(volumes):
            volume_type = next(
                (
                    vol["VolumeType"]
                    for vol in ebs_volume_information
                    if vol["VolumeId"] == volume
                ),
                None,
            )
            if verbose:
                print(f"Volume type: {volume_type} for volume {volume}")

            metrics = [
                [
                    "AWS/EBS",
                    "VolumeTotalWriteTime",
                    "VolumeId",
                    volume,
                    {
                        "region": region,
                        "id": "m1",
                        "label": f"{volume}_VolumeTotalWriteTime",
                        "visible": False,
                        "color": "#69ae34",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeWriteOps",
                    "VolumeId",
                    volume,
                    {
                        "region": region,
                        "id": "m2",
                        "label": f"{volume}_VolumeWriteOps",
                        "visible": False,
                        "color": "#69ae34",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeQueueLength",
                    "VolumeId",
                    volume,
                    {
                        "region": region,
                        "id": "m3",
                        "label": f"{volume}_VolumeQueueLength",
                        "yAxis": "right",
                        "color": "#08aad2",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeTotalReadTime",
                    "VolumeId",
                    volume,
                    {
                        "region": region,
                        "id": "m4",
                        "label": f"{volume}_VolumeTotalReadTime",
                        "visible": False,
                        "color": "#dfb52c",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeReadOps",
                    "VolumeId",
                    volume,
                    {
                        "region": region,
                        "id": "m5",
                        "label": f"{volume}_VolumeReadOps",
                        "visible": False,
                        "color": "#dfb52c",
                    },
                ],
            ]

            metrics.append(
                [
                    {
                        "expression": "(m1 / m2) * 1000",
                        "label": f"{volume}_WriteLatency",
                        "id": "e1",
                        "region": region,
                        "yAxis": "left",
                        "color": "#69ae34",
                    }
                ]
            )
            metrics.append(
                [
                    {
                        "expression": "(m4 / m5) * 1000",
                        "label": f"{volume}_ReadLatency",
                        "id": "e2",
                        "region": region,
                        "yAxis": "left",
                        "color": "#dfb52c",
                    }
                ]
            )
            metrics.append(
                [
                    {
                        "expression": "IF(m3>0 AND m2+m5==0, 1, 0)",
                        "label": f"{volume}_ImpairedVol",
                        "id": "e3",
                        "region": region,
                        "yAxis": "left",
                        "color": "#fe6e73",
                    }
                ]
            )

            if volume_type in ["sc1", "st1"]:
                if verbose:
                    print(
                        f"Adding BurstBalance for {volume} as it is a {volume_type} volume type"
                    )
                metrics.append(
                    [
                        "AWS/EBS",
                        "BurstBalance",
                        "VolumeId",
                        volume,
                        {
                            "region": region,
                            "id": "m6",  # ID for BurstBalance metric
                            "label": f"{volume}_BurstBalance",
                            "color": "#f0ad4e",
                        },
                    ]
                )

            widget_metrics_count = len(metrics)
            current_metric_count += widget_metrics_count

            # Check if we exceed the limit
            if current_metric_count > Config.DASHBOARD_METRICS_LIMIT:
                # Create a new dashboard for the previous widgets
                dashboard_name = create_new_dashboard(
                    cloudwatch=cloudwatch,
                    widgets=widgets,
                    tag_name=tag_name,
                    tag_value=tag_value,
                    current_dashboard_number=current_dashboard_number,
                    verbose=verbose,
                    dry_run=dry_run,
                )
                new_dashboards.append(dashboard_name)

                # Reset counters and lists for the new dashboard
                widgets = []
                current_dashboard_number += 1
                current_metric_count = (
                    widget_metrics_count  # Reset to the current widget's metric count
                )

            widgets.append(
                {
                    "type": "metric",
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": metrics,
                        "view": "timeSeries",
                        "stacked": False,
                        "region": region,
                        "title": f"EBS Metrics for {volume}",
                        "period": 60,
                        "stat": "Average",
                    },
                }
            )

        # Create the last dashboard if there are any widgets left
        if widgets:
            total_dashboards = current_dashboard_number  # Final dashboard count
            dashboard_name = create_new_dashboard(
                cloudwatch=cloudwatch,
                widgets=widgets,
                tag_name=tag_name,
                tag_value=tag_value,
                current_dashboard_number=current_dashboard_number,
                verbose=verbose,
                dry_run=dry_run,
            )
            new_dashboards.append(dashboard_name)

            if verbose:
                print("\n\n=== Dashboards Created ===\n")
                print("\n".join(new_dashboards))

    return new_dashboards


def create_new_dashboard(
    cloudwatch,
    widgets,
    tag_name,
    tag_value,
    current_dashboard_number,
    verbose,
    dry_run,
):
    dashboard_name = f"EBS_{tag_name}_{tag_value}_{current_dashboard_number}"
    dashboard_name = "".join(e if e.isalnum() else "_" for e in dashboard_name)
    dashboard_body = json.dumps({"widgets": widgets})

    if verbose or dry_run:
        print("Dashboard JSON:")
        print(dashboard_body)

    if not dry_run:
        print(f"\nPutting dashboard: {dashboard_name}")
        response = cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=dashboard_body,
        )
        if verbose:
            print(f"Put Dashboard {dashboard_name} Response:")
            print(response)

    return dashboard_name


def list_existing_dashboards(cloudwatch, tag_name):
    dashboard_names = []
    dashboards = cloudwatch.list_dashboards()
    pattern = f"EBS_{tag_name}_" if tag_name else "EBS_"

    for dashboard in dashboards.get("DashboardEntries", []):
        dashboard_name = dashboard.get("DashboardName", "")
        if dashboard_name.startswith(pattern):
            dashboard_names.append(dashboard_name)

    return dashboard_names


def dashboard_cleanup(cloudwatch, current_dashboards, new_dashboards):
    for dashboard in current_dashboards:
        if dashboard not in new_dashboards:
            print(f"\nRemoving stale dashboard: {dashboard}")
            cloudwatch.delete_dashboards(DashboardNames=[dashboard])


def get_tag_data(ebs_volumes):
    tag_data = collections.defaultdict(set)

    for volume in ebs_volumes:
        if volume is None:  # Add this check
            continue
        tags = volume.get("Tags", {})
        for key, value in tags.items():
            tag_data[key].add(value)
    return tag_data


def get_tag_data(ebs_volumes):
    tag_data = collections.defaultdict(set)

    for volume in ebs_volumes:
        if volume is None:  # Add this check
            continue
        tags = volume.get("Tags", {})
        for key, value in tags.items():
            tag_data[key].add(value)

    return tag_data


def get_volume_tags(volume, tag_name):
    for tag in volume.get("Tags", []):
        if tag["Key"] == tag_name:
            return tag["Value"]
    return None


def filter_volumes_by_tag(ebs_volume_information, tag_name):
    volumes_by_tag = {}
    for volume in ebs_volume_information:
        tag_value = get_volume_tags(volume, tag_name)
        if tag_value:
            volumes_by_tag.setdefault(tag_value, []).append(volume["VolumeId"])
    return volumes_by_tag


def get_all_volumes(ec2_client):
    paginator = ec2_client.get_paginator("describe_volumes")
    all_volumes = []

    for page in paginator.paginate(MaxResults=Config.PAGINATION_COUNT):
        if page.get("Volumes") is not None:  # Add this check
            all_volumes.extend(page["Volumes"])

    return all_volumes


def get_ebs_volumes(ec2_client, tag_name=None, verbose=False):
    all_volumes = get_all_volumes(ec2_client)

    if verbose:
        print("All Volumes:", all_volumes)  # Debug print

    if tag_name:
        volumes_by_tag = filter_volumes_by_tag(all_volumes, tag_name)
        if verbose:
            print(f"Found {len(volumes_by_tag)} tagged volumes")
        return volumes_by_tag
    else:
        return {None: [volume["VolumeId"] for volume in all_volumes]}


def get_ebs_volume_information(ec2_client):
    paginator = ec2_client.get_paginator("describe_volumes")
    all_volume_info = []

    for page in paginator.paginate(MaxResults=Config.PAGINATION_COUNT):
        for volume in page["Volumes"]:
            all_volume_info.append(volume)

    return all_volume_info


def get_ebs_volumes(ec2_client, tag_name=None, verbose=False):
    all_volumes = get_all_volumes(ec2_client)

    if tag_name:
        volumes_by_tag = filter_volumes_by_tag(all_volumes, tag_name)
        if verbose:
            print(f"Found {len(volumes_by_tag)} tagged volumes")
        return volumes_by_tag
    else:
        return {None: [volume["VolumeId"] for volume in all_volumes]}


def initialize_logging(loglevel):
    logging.basicConfig(level=getattr(logging, loglevel.upper()))


def list_unique_tag_names(ebs_volumes):
    unique_tag_names = set()

    for volume in ebs_volumes:
        if volume is None:
            continue
        tags = volume.get("Tags", [])
        for tag in tags:
            unique_tag_names.add(tag["Key"])

    print("Unique EBS Volume Tag Names:")
    for tag_name in unique_tag_names:
        print(f" - {tag_name}")


def initialize_aws_clients(region):
    try:
        ec2_client = boto3.client("ec2", region_name=region)
        ec2_resource = boto3.resource("ec2", region_name=region)
        cloudwatch = boto3.client("cloudwatch", region_name=region)
        logging.info("Initilized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)

    return ec2_client, cloudwatch


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Dashboard for EBS Volumes"
    )
    parser.add_argument("--tag-name", help="Tag name to filter EBS volumes")
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="Specify the AWS Region. Defaults to us-west-2.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print debug statements")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print dashboard JSON but do not create it",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not delete stale dashboards",
    )
    parser.add_argument(
        "--list-tag-names",
        action="store_true",
        help="List all unique EBS volue tag names",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="List all EBS volue tag names and a list of unique values",
    )
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
