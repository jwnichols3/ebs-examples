import boto3
import argparse
import json


class Config:
    PAGINATION_COUNT = 300  # Set the number of items per page
    DASHBOARD_NAME = "EBS_Latency_Dashboard"
    DASHBOARD_PERIOD = 60
    DASHBOARD_WIDGET_WIDTH = 6
    DASHBOARD_WIDGET_HEIGHT = 6
    DASHBOARD_REGION = "us-west-2"  # Default region if no region provided


def main():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Dashboard for EBS Read and Write Latency"
    )
    parser.add_argument("--verbose", action="store_true", help="Print debug statements")
    parser.add_argument(
        "--region",
        default=Config.DASHBOARD_REGION,
        help=f"AWS Region (defaults to {Config.DASHBOARD_REGION}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print dashboard JSON but do not create it",
    )
    args = parser.parse_args()

    if args.region:
        Config.DASHBOARD_REGION = args.region

    create_dashboard(verbose=args.verbose, dry_run=args.dry_run)


def get_ebs_volumes():
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_volumes")  # Create a paginator
    volumes = []

    # Iterate through each page of results
    for page in paginator.paginate(MaxResults=Config.PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volumes.append(volume["VolumeId"])

    return volumes


def create_dashboard(verbose=False, dry_run=False):
    cloudwatch = boto3.client("cloudwatch")
    volumes = get_ebs_volumes()

    widgets = []
    # y_position = 0  # Initial Y-coordinate position for the widget

    for i, volume in enumerate(volumes):
        print(f"Constructing {volume}...")
        metrics = [
            [
                {
                    "expression": f"(m{i*4+2}/m{i*4+1})*1000",
                    "label": f"{volume}_ReadLatency",
                    "id": f"e{i*2+1}",
                    "region": Config.DASHBOARD_REGION,
                }
            ],
            [
                {
                    "expression": f"(m{i*4+4}/m{i*4+3})*1000",
                    "label": f"{volume}_WriteLatency",
                    "id": f"e{i*2+2}",
                    "region": Config.DASHBOARD_REGION,
                }
            ],
            [
                "AWS/EBS",
                "VolumeReadOps",
                "VolumeId",
                volume,
                {
                    "region": Config.DASHBOARD_REGION,
                    "visible": False,
                    "id": f"m{i*4+1}",
                    "label": f"{volume}_VolumeReadOps",
                },
            ],
            [
                "AWS/EBS",
                "VolumeTotalReadTime",
                "VolumeId",
                volume,
                {
                    "region": Config.DASHBOARD_REGION,
                    "visible": False,
                    "id": f"m{i*4+2}",
                    "label": f"{volume}_VolumeTotalReadTime",
                },
            ],
            [
                "AWS/EBS",
                "VolumeWriteOps",
                "VolumeId",
                volume,
                {
                    "region": Config.DASHBOARD_REGION,
                    "visible": False,
                    "id": f"m{i*4+3}",
                    "label": f"{volume}_VolumeWriteOps",
                },
            ],
            [
                "AWS/EBS",
                "VolumeTotalWriteTime",
                "VolumeId",
                volume,
                {
                    "region": Config.DASHBOARD_REGION,
                    "visible": False,
                    "id": f"m{i*4+4}",
                    "label": f"{volume}_VolumeTotalWriteTime",
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
                "title": f"EBS-Latency ({volume})",
                "period": Config.DASHBOARD_PERIOD,
                "stat": "Average",
            },
        }
        widgets.append(widget)

        # y_position += 6  # Update the Y-coordinate position for the next widget

    dashboard_body = json.dumps({"widgets": widgets})

    if verbose or dry_run:
        print("Dashboard JSON:")
        print(dashboard_body)

    if not dry_run:
        print(f"Putting dashboard...")
        response = cloudwatch.put_dashboard(
            DashboardName=Config.DASHBOARD_NAME,
            DashboardBody=dashboard_body,
        )
        print("Put Dashboard Response:")
        print(response)


if __name__ == "__main__":
    main()
