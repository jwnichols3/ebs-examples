import boto3
import argparse
import json


class Config:
    EBS_REGION = "us-west-2"  # Default reigon if no --ebs-region provided
    DASHBOARD_NAME_PREFIX = "EBS_Review"
    DASHBOARD_PERIOD = 60
    DASHBOARD_WIDGET_WIDTH = 6
    DASHBOARD_WIDGET_HEIGHT = 6
    DASHBOARD_REGION = (
        "us-west-2"  # Default CloudWatch region if no --cw-region provided
    )
    PAGINATION_COUNT = 300  # Set the number of items per page
    DASHBOARD_METRICS_LIMIT = (
        2500  # The limit of CloudWatch metrics allowed on a Dashboard.
    )


def main():
    args = parse_args()

    if args.cw_region:
        Config.DASHBOARD_REGION = args.cw_region

    if args.ebs_region:
        Config.EBS_REGION = args.ebs_region

    tag_name, tag_value = args.tag if args.tag else (None, None)

    default_prefix = Config.DASHBOARD_NAME_PREFIX
    if tag_name and tag_value:
        Config.DASHBOARD_NAME_PREFIX = f"{default_prefix}_{tag_name}_{tag_value}"
    else:
        Config.DASHBOARD_NAME_PREFIX = f"{default_prefix}_All"

    volumes = get_ebs_volumes(Config.EBS_REGION, tag_name, tag_value)

    create_dashboard(
        ebs_region=Config.EBS_REGION,
        cw_region=Config.DASHBOARD_REGION,
        volumes=volumes,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    # Cleanup stale dashboards
    dashboard_search_prefix = f"{Config.DASHBOARD_NAME_PREFIX}_{Config.EBS_REGION}"
    existing_dashboards = list_existing_dashboards(
        Config.DASHBOARD_REGION, dashboard_search_prefix
    )
    total_shards = create_dashboard_shards(
        get_ebs_volumes(Config.EBS_REGION), 8
    )  # Assume 8 metrics per volume
    valid_dashboards = [
        f"{Config.DASHBOARD_NAME_PREFIX}_{Config.EBS_REGION}_{i}"
        for i in range(1, len(total_shards) + 1)
    ]
    stale_dashboards = set(existing_dashboards) - set(valid_dashboards)

    if stale_dashboards:
        print(f"Cleaning up {len(stale_dashboards)} dashboards...")
        delete_dashboards(Config.DASHBOARD_REGION, list(stale_dashboards))


def get_ebs_volumes(ebs_region, tag_name=None, tag_value=None):
    ec2 = boto3.client("ec2", region_name=ebs_region)

    filters = []

    if tag_name and tag_value:
        filters.append({"Name": f"tag:{tag_name}", "Values": [tag_value]})
    paginator = ec2.get_paginator("describe_volumes")
    volumes = []

    for page in paginator.paginate(Filters=filters, MaxResults=Config.PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volumes.append(volume["VolumeId"])

    return volumes


def create_dashboard_shards(volumes, max_metrics_per_volume):
    max_volumes_per_shard = Config.DASHBOARD_METRICS_LIMIT // max_metrics_per_volume
    shards = {}
    shard_count = 1  # Initialize shard count
    shard_volumes = []  # Initialize list to hold volumes for the current shard

    for volume in volumes:
        if len(shard_volumes) >= max_volumes_per_shard:
            shards[shard_count] = shard_volumes  # Add the current shard
            shard_count += 1  # Increment the shard count
            shard_volumes = []  # Reset the list for the next shard

        shard_volumes.append(volume)  # Add the current volume to the current shard

    if shard_volumes:  # Add the last shard if it's not empty
        shards[shard_count] = shard_volumes

    return shards


def create_dashboard(cw_region, ebs_region, volumes, verbose=False, dry_run=False):
    cloudwatch = boto3.client("cloudwatch", region_name=cw_region)
    #    volumes = get_ebs_volumes(ebs_region)

    # Get metrics for the first volume to determine metrics per volume
    _, max_metrics_per_volume = get_metrics_for_volume(0, volumes[0], ebs_region)

    # Calculate shards
    shards = create_dashboard_shards(volumes, max_metrics_per_volume)

    # Loop over each shard to create dashboard
    for shard_num, shard_volumes in shards.items():
        widgets = []
        total_metrics = 0

        for i, volume_id in enumerate(shard_volumes):
            metrics, metrics_count = get_metrics_for_volume(i, volume_id, ebs_region)
            total_metrics += metrics_count

            widget = {
                "type": "metric",
                "width": Config.DASHBOARD_WIDGET_WIDTH,
                "height": Config.DASHBOARD_WIDGET_HEIGHT,
                "properties": {
                    "metrics": metrics,
                    "view": "timeSeries",
                    "stacked": False,
                    "region": Config.DASHBOARD_REGION,
                    "title": f"EBS {volume_id} {ebs_region}",
                    "period": Config.DASHBOARD_PERIOD,
                    "stat": "Average",
                },
            }
            widgets.append(widget)

        dashboard_name = f"{Config.DASHBOARD_NAME_PREFIX}_{ebs_region}_{shard_num}"
        dashboard_body = json.dumps({"widgets": widgets})

        if verbose or dry_run:
            print(f"Dashboard Name: {dashboard_name}")
            print(
                f"Total volumes: {len(shard_volumes)}\nTotal metrics: {total_metrics}"
            )
            print("Dashboard JSON:")
            print(dashboard_body)

        if not dry_run:
            print(f"Putting dashboard {dashboard_name}...")
            print(
                f"Total volumes: {len(shard_volumes)}\nTotal metrics: {total_metrics}"
            )
            response = cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=dashboard_body,
            )
            print("Put Dashboard Response:")
            print(response)


def get_metrics_for_volume(i, volume_id, ebs_region):
    metrics = [
        [
            "AWS/EBS",
            "VolumeTotalWriteTime",
            "VolumeId",
            volume_id,
            {
                "region": ebs_region,
                "id": "m1",
                "label": "VolumeTotalWriteTime",
                "visible": False,
                "yAxis": "left",
                "color": "#69ae34",
            },
        ],
        [
            "AWS/EBS",
            "VolumeWriteOps",
            "VolumeId",
            volume_id,
            {
                "region": ebs_region,
                "id": "m2",
                "label": "VolumeWriteOps",
                "visible": False,
                "yAxis": "left",
                "color": "#69ae34",
            },
        ],
        [
            "AWS/EBS",
            "VolumeQueueLength",
            "VolumeId",
            volume_id,
            {
                "region": ebs_region,
                "id": "m3",
                "label": "VolumeQueueLength",
                "visible": True,
                "yAxis": "left",
                "color": "#08aad2",
            },
        ],
        [
            "AWS/EBS",
            "VolumeTotalReadTime",
            "VolumeId",
            volume_id,
            {
                "region": ebs_region,
                "id": "m4",
                "label": "VolumeTotalReadTime",
                "visible": False,
                "yAxis": "left",
                "color": "#dfb52c",
            },
        ],
        [
            "AWS/EBS",
            "VolumeReadOps",
            "VolumeId",
            volume_id,
            {
                "region": ebs_region,
                "id": "m5",
                "label": "VolumeReadOps",
                "visible": False,
                "yAxis": "left",
                "color": "#dfb52c",
            },
        ],
        [
            {
                "expression": "(m1 / m2) * 1000",
                "label": "WriteLatency",
                "id": "e1",
                "region": ebs_region,
                "visible": True,
                "yAxis": "left",
                "color": "#69ae34",
            }
        ],
        [
            {
                "expression": "(m4 / m5) * 1000",
                "label": "ReadLatency",
                "id": "e2",
                "region": ebs_region,
                "visible": True,
                "yAxis": "left",
                "color": "#dfb52c",
            }
        ],
        [
            {
                "expression": "IF(m3>0 AND m2+m5==0, 1, 0)",
                "label": "ImpairedVol",
                "id": "e3",
                "region": ebs_region,
                "visible": True,
                "yAxis": "right",
                "color": "#fe6e73",
            },
        ],
    ]

    return metrics, len(metrics)


def list_existing_dashboards(cw_region, dashboard_name_prefix):
    cloudwatch = boto3.client("cloudwatch", region_name=cw_region)
    dashboards = cloudwatch.list_dashboards(DashboardNamePrefix=dashboard_name_prefix)[
        "DashboardEntries"
    ]
    return [d["DashboardName"] for d in dashboards]


def delete_dashboards(cw_region, dashboard_names):
    cloudwatch = boto3.client("cloudwatch", region_name=cw_region)
    for name in dashboard_names:
        cloudwatch.delete_dashboards(DashboardNames=[name])
        print(f"Deleted dashboard: {name}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Dashboard for EBS volumes."
    )
    parser.add_argument(
        "--tag",
        nargs=2,
        metavar=("TagName", "TagValue"),
        help="TagName and TagValue to filter EBS volumes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prints the Dashbaord body but does not update the CloudWatch Dashboard.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print details of boto3 calls."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print debug level logging."
    )
    parser.add_argument(
        "--ebs-region",
        help=f"AWS region name to collect EBS volumes from. Default is {Config.EBS_REGION}.",
    )
    parser.add_argument(
        "--cw-region", help=f"AWS region name. Default is {Config.DASHBOARD_REGION}."
    )
    parser.add_argument(
        "--read",
        action="store_true",
        help="Read the content of the existing dashboard.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
