import boto3
import argparse
import json


class Config:
    PAGINATION_COUNT = 300  # Set the number of items per page
    DASHBOARD_NAME = "EBS_Dashboard_VolumeStatus"
    DASHBOARD_PERIOD = 60
    DASHBOARD_WIDGET_WIDTH = 6
    DASHBOARD_WIDGET_HEIGHT = 6
    DASHBOARD_REGION = (
        "us-west-2"  # Default CloudWatch region if no --cw-region provided
    )
    DASHBOARD_METRICS_LIMIT = (
        2500  # The limit of CloudWatch metrics allowed on a Dashboard.
    )
    EBS_REGION = "us-west-2"  # Default reigon if no --ebs-region provided


def main():
    args = parse_args()

    if args.cw_region:
        Config.DASHBOARD_REGION = args.cw_region

    if args.ebs_region:
        Config.EBS_REGION = args.ebs_region

    create_dashboard(
        ebs_region=Config.EBS_REGION,
        cw_region=Config.DASHBOARD_REGION,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )


def get_ebs_volumes(ebs_region):
    ec2 = boto3.client("ec2", region_name=ebs_region)
    paginator = ec2.get_paginator("describe_volumes")  # Create a paginator
    volumes = []

    # Iterate through each page of results
    for page in paginator.paginate(MaxResults=Config.PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volumes.append(volume["VolumeId"])

    return volumes


def create_dashboard(cw_region, ebs_region, verbose=False, dry_run=False):
    cloudwatch = boto3.client("cloudwatch", region_name=cw_region)

    volumes = get_ebs_volumes(ebs_region)

    widgets = []

    for i, volume_id in enumerate(volumes):
        print(f"Constructing {volume_id}...")

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

        widget = {
            "type": "metric",
            "width": Config.DASHBOARD_WIDGET_WIDTH,
            "height": Config.DASHBOARD_WIDGET_HEIGHT,
            "properties": {
                "metrics": metrics,
                "view": "timeSeries",
                "stacked": False,
                "region": Config.DASHBOARD_REGION,
                "title": f"EBS ({volume_id})",
                "period": Config.DASHBOARD_PERIOD,
                "stat": "Average",
            },
        }
        widgets.append(widget)

    dashboard_body = json.dumps({"widgets": widgets})

    if verbose or dry_run:
        print("Dashboard JSON:")
        print(dashboard_body)

    if not dry_run:
        print("Putting dashboard...")
        response = cloudwatch.put_dashboard(
            DashboardName=Config.DASHBOARD_NAME,
            DashboardBody=dashboard_body,
        )
        print("Put Dashboard Response:")
        print(response)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Dashboard for EBS volumes."
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
