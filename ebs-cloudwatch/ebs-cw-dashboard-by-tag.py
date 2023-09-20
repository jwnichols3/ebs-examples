import boto3
import argparse
import json
import logging
import sys

PAGINATION_COUNT = 300  # Set the number of items per page
DASHBOARD_METRICS_LIMIT = 2500  # Set the number of metrics per dashboard.


def main():
    args = parse_args()

    initialize_logging(args.loglevel)

    ec2_client, cloudwatch = initialize_aws_clients(region=args.region)

    current_dashboards = list_existing_dashboards(cloudwatch, args.tag_name)

    new_dashboards = construct_dashboard(
        ec2_client=ec2_client,
        cloudwatch=cloudwatch,
        tag_name=args.tag_name,
        region=args.region,
        verbose=args.verbose,
        dry_run=args.dry_run,
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
    ec2_client,
    cloudwatch,
    region,
    tag_name=None,
    verbose=False,
    dry_run=False,
):
    new_dashboards = []
    dashboard_name = ""

    volumes_by_tag = get_ebs_volumes(
        ec2_client=ec2_client, tag_name=tag_name, verbose=verbose
    )

    for tag_value, volumes in volumes_by_tag.items():
        current_metric_count = 0
        current_dashboard_number = 1
        widgets = []

        for i, volume in enumerate(volumes):
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

            widget_metrics_count = len(metrics)
            current_metric_count += widget_metrics_count

            # Check if we exceed the limit
            if current_metric_count > DASHBOARD_METRICS_LIMIT:
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


def get_volume_tags(volume, tag_name):
    for tag in volume.get("Tags", []):
        if tag["Key"] == tag_name:
            return tag["Value"]
    return None


def filter_volumes_by_tag(volumes, tag_name):
    volumes_by_tag = {}
    for volume in volumes:
        tag_value = get_volume_tags(volume, tag_name)
        if tag_value:
            volumes_by_tag.setdefault(tag_value, []).append(volume["VolumeId"])
    return volumes_by_tag


def get_all_volumes(ec2_client):
    paginator = ec2_client.get_paginator("describe_volumes")
    all_volumes = []

    for page in paginator.paginate(MaxResults=PAGINATION_COUNT):
        all_volumes.extend(page["Volumes"])

    return all_volumes


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
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
