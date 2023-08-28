import boto3
import argparse
import json

PAGINATION_COUNT = 300  # Set the number of items per page


def get_ebs_volumes():
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_volumes")  # Create a paginator
    volumes = []

    # Iterate through each page of results
    for page in paginator.paginate(MaxResults=PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volumes.append(volume["VolumeId"])

    return volumes


def create_dashboard(verbose=False, dry_run=False):
    cloudwatch = boto3.client("cloudwatch")
    volumes = get_ebs_volumes()

    metrics = []
    for i, volume in enumerate(volumes):
        print(f"Constructing {volume}...")
        metrics.extend(
            [
                [
                    {
                        "expression": f"(m{i*4+2}/m{i*4+1})*1000",
                        "label": f"{volume}_ReadLatency",
                        "id": f"e{i*2+1}",
                        "region": "us-west-2",
                    }
                ],
                [
                    {
                        "expression": f"(m{i*4+4}/m{i*4+3})*1000",
                        "label": f"{volume}_WriteLatency",
                        "id": f"e{i*2+2}",
                        "region": "us-west-2",
                    }
                ],
                [
                    "AWS/EBS",
                    "VolumeReadOps",
                    "VolumeId",
                    volume,
                    {
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
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
                        "region": "us-west-2",
                        "visible": False,
                        "id": f"m{i*4+4}",
                        "label": f"{volume}_VolumeTotalWriteTime",
                    },
                ],
            ]
        )

    dashboard_body = json.dumps(
        {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": metrics,
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-west-2",
                        "title": f"EBS-Latency ({volume})",
                        "period": 300,
                        "stat": "Average",
                    },
                }
            ]
        }
    )

    if verbose or dry_run:
        print("Dashboard JSON:")
        print(dashboard_body)

    if not dry_run:
        print(f"Putting dashboard...")
        response = cloudwatch.put_dashboard(
            DashboardName="Read_and_Write_Latency",  # Updated Dashboard Name
            DashboardBody=dashboard_body,
        )
        print("Put Dashboard Response:")
        print(response)


def main():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Dashboard for EBS Read and Write Latency"
    )
    parser.add_argument("--verbose", action="store_true", help="Print debug statements")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print dashboard JSON but do not create it",
    )
    args = parser.parse_args()

    create_dashboard(verbose=args.verbose, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
