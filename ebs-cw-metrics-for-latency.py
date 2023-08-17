import boto3
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

PAGINATOR_COUNT = 300


def get_metrics(cloudwatch, metric_name, volume_id, start_time, end_time):
    paginator = cloudwatch.get_paginator("get_metric_data")
    response_iterator = paginator.paginate(
        MetricDataQueries=[
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": metric_name,
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 60,
                    "Stat": "Average",
                },
                "ReturnData": True,
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        PaginationConfig={"PageSize": PAGINATOR_COUNT},
    )

    data_points = []
    for response in response_iterator:
        data_points.extend(
            zip(
                response["MetricDataResults"][0]["Timestamps"],
                response["MetricDataResults"][0]["Values"],
            )
        )

    return data_points


def get_volume_details(ec2, volume_id):
    response = ec2.describe_volumes(VolumeIds=[volume_id])
    volume = response["Volumes"][0]
    volume_details = {
        "Volume ID": volume["VolumeId"],
        "Volume Name": volume["Tags"][0]["Value"] if "Tags" in volume else "N/A",
        "Volume Status": volume["State"],
        "EC2 Instance ID": "N/A",
        "EC2 Name": "N/A",
        "Creation Time": volume["CreateTime"].astimezone(),
    }

    if volume["Attachments"]:
        instance_id = volume["Attachments"][0]["InstanceId"]
        volume_details["EC2 Instance ID"] = instance_id

        instance_response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = instance_response["Reservations"][0]["Instances"][0]
        instance_name = next(
            (tag["Value"] for tag in instance["Tags"] if tag["Key"] == "Name"), "N/A"
        )
        volume_details["EC2 Name"] = instance_name

    return volume_details


def main(volume_id, table_style):
    ec2 = boto3.client("ec2")
    cloudwatch = boto3.client("cloudwatch")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    volume_details = get_volume_details(ec2, volume_id)

    metrics = [
        "VolumeReadOps",
        "VolumeTotalReadTime",
        "VolumeWriteOps",
        "VolumeTotalWriteTime",
    ]

    table_data = {}
    for metric_name in metrics:
        print(f"Fetching data for metric: {metric_name}")
        data_points = get_metrics(
            cloudwatch, metric_name, volume_id, start_time, end_time
        )
        for timestamp, value in data_points:
            local_timestamp = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            utc_timestamp = timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )  # Format the UTC time
            if timestamp not in table_data:
                table_data[timestamp] = [
                    local_timestamp,
                    utc_timestamp,
                ]  # Add the UTC time to the table
            table_data[timestamp].append(value)

    print("Volume Details:")
    print(tabulate(volume_details.items(), tablefmt=table_style))

    headers = [
        "Local",
        "UTC",
        "VolumeReadOps",
        "VolumeTotalReadTime",
        "VolumeWriteOps",
        "VolumeTotalWriteTime",
    ]
    table = sorted(table_data.values())
    print(tabulate(table, headers=headers, tablefmt=table_style))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch EBS Volume Metrics")
    parser.add_argument("--volume-id", required=True, help="EBS Volume ID")
    parser.add_argument(
        "--style",
        choices=["tsv", "simple", "pretty", "plain", "github", "grid", "fancy"],
        default="simple",
        help="Table style",
    )
    args = parser.parse_args()
    main(args.volume_id, args.style)
