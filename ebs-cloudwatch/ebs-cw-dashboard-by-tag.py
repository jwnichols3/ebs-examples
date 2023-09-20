import boto3
import argparse
import json

PAGINATION_COUNT = 300  # Set the number of items per page


def main():
    args = parse_args()

    create_dashboard(tag_name=args.tag_name, verbose=args.verbose, dry_run=args.dry_run)


def get_ebs_volumes(tag_name=None, verbose=False):
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_volumes")
    volumes_by_tag = {}

    for page in paginator.paginate(MaxResults=PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            tag_value = None

            if tag_name:
                for tag in volume.get("Tags", []):
                    if tag["Key"] == tag_name:
                        tag_value = tag["Value"]

            if tag_value:  # Only add volumes that have a non-blank tag value
                volumes_by_tag.setdefault(tag_value, []).append(volume_id)

    if verbose:
        print(f"Found {len(volumes_by_tag)} tagged volumes")

    return volumes_by_tag if tag_name else {None: [v["VolumeId"] for v in volumes]}


def create_dashboard(tag_name=None, verbose=False, dry_run=False):
    cloudwatch = boto3.client("cloudwatch")
    volumes_by_tag = get_ebs_volumes(tag_name=tag_name, verbose=verbose)

    for tag_value, volumes in volumes_by_tag.items():
        widgets = []

        for i, volume in enumerate(volumes):
            metrics = [
                [
                    "AWS/EBS",
                    "VolumeTotalWriteTime",
                    "VolumeId",
                    volume,
                    {
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
                        "yAxis": "left",
                        "color": "#fe6e73",
                    }
                ]
            )

            widgets.append(
                {
                    "type": "metric",
                    #                    "x": 0,
                    #                    "y": i * 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": metrics,
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-west-2",
                        "title": f"EBS Metrics for {volume}",
                        "period": 60,
                        "stat": "Average",
                    },
                }
            )

        dashboard_name = f"EBS_{tag_name}_{tag_value}" if tag_name else "EBS_Dashboard"
        dashboard_name = "".join(e if e.isalnum() else "_" for e in dashboard_name)

        dashboard_body = json.dumps({"widgets": widgets})

        if verbose or dry_run:
            print("Dashboard JSON:")
            print(dashboard_body)

        if not dry_run:
            print(f"Putting dashboard: {dashboard_name}")
            response = cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=dashboard_body,
            )
            print("Put Dashboard Response:")
            print(response)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Dashboard for EBS Volumes"
    )
    parser.add_argument("--tag-name", help="Tag name to filter EBS volumes")
    parser.add_argument("--verbose", action="store_true", help="Print debug statements")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print dashboard JSON but do not create it",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
