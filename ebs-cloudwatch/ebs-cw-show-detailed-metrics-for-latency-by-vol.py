import boto3
import argparse
from datetime import datetime, timedelta
from pytz import utc
from tabulate import tabulate
from botocore.exceptions import ClientError, BotoCoreError

PAGINATOR_COUNT = 300


def main(
    volume_id,
    table_style,
    metrics,
    output_to_file=False,
    start_date=None,
    end_date=None,
):
    ec2, cloudwatch = initialize_aws_clients()

    # Validate API limits for the number of metrics and date range
    if len(metrics) > 500:
        print("Too many metrics requested, exceeding CloudWatch API limit of 500.")
        return

    if start_date and end_date:
        delta = end_date - start_date
        if delta.days * len(metrics) * 24 > 100800:
            print(
                "Requested time range and metrics exceed CloudWatch API limit of 100,800 data points."
            )
            return

    start_time, end_time = get_time_range(start_date, end_date)

    try:
        volume_details = get_volume_details(ec2, volume_id)
        if not volume_details:
            print(f"Volume ID {volume_id} invalid or volume not found.")
            return
    except (ClientError, BotoCoreError) as e:
        print(f"Error getting volume details for {volume_id}: {e}")
        return

    print(f"Fetching data for metrics: {', '.join(metrics)}")
    all_data_points = get_metrics(cloudwatch, metrics, volume_id, start_time, end_time)

    table_data = {}
    for metric, data_points in all_data_points.items():
        for timestamp, value in data_points:
            local_timestamp = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            utc_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

            if timestamp not in table_data:
                table_data[timestamp] = [local_timestamp, utc_timestamp]

            while len(table_data[timestamp]) <= metrics.index(metric) + 2:
                table_data[timestamp].append(None)

            table_data[timestamp][metrics.index(metric) + 2] = value

    print_volume_details(volume_details, table_style, start_time, end_time)
    headers = ["Local", "UTC"] + metrics
    table = sorted(table_data.values())
    print_metrics_table(table, headers, table_style)

    if output_to_file:
        file_name = f"{volume_details.get('Volume ID', 'unknown')}.tsv"
        with open(file_name, "w") as f:
            f.write(tabulate(table, headers=headers, tablefmt="tsv"))
        print(f"Results written to {file_name}")


def get_metrics(cloudwatch, metrics, volume_id, start_time, end_time):
    try:
        metric_data_queries = [
            {
                "Id": f"m{i}",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": metric,
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 60,
                    "Stat": "Average",
                },
                "ReturnData": True,
            }
            for i, metric in enumerate(metrics)
        ]

        paginator = cloudwatch.get_paginator("get_metric_data")
        response_iterator = paginator.paginate(
            MetricDataQueries=metric_data_queries,
            StartTime=start_time,
            EndTime=end_time,
            PaginationConfig={"PageSize": PAGINATOR_COUNT},
        )

        data_points = {metric: [] for metric in metrics}

        for response in response_iterator:
            for i, metric in enumerate(metrics):
                metric_data = zip(
                    response["MetricDataResults"][i]["Timestamps"],
                    response["MetricDataResults"][i]["Values"],
                )
                data_points[metric].extend(metric_data)

        return data_points
    except (ClientError, BotoCoreError) as e:
        print(f"Error fetching metrics: {e}")
        return ()


def get_volume_details(ec2, volume_id):
    try:
        response = ec2.describe_volumes(VolumeIds=[volume_id])
    except (ClientError, BotoCoreError) as e:
        print(f"Error fetching volume details: {e}")
        return None

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


def initialize_aws_clients():
    ec2 = boto3.client("ec2")
    cloudwatch = boto3.client("cloudwatch")
    return ec2, cloudwatch


def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}")


def get_time_range(start_date=None, end_date=None):
    if start_date and end_date:
        start_date = start_date.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=utc
        )
        end_date = end_date.replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=utc
        )
        return start_date, end_date
    else:
        end_time = datetime.utcnow().replace(tzinfo=utc)
        start_time = end_time - timedelta(hours=24)
        return start_time, end_time


def print_volume_details(volume_details, table_style, start_time, end_time):
    print("Volume Details:")
    print(f"Start Time: {start_time}")
    print(f"End Time:   {end_time}")
    print(tabulate(volume_details.items(), tablefmt=table_style))


def print_metrics_table(table_data, headers, table_style):
    table = sorted(table_data)
    print(tabulate(table, headers=headers, tablefmt=table_style))


def parse_args():
    """
    Parses command-line arguments.
    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Fetch EBS Volume Metrics")
    parser.add_argument("--volume-id", required=True, help="EBS Volume ID")
    parser.add_argument(
        "--start", type=validate_date, help="Start date in format YYYY-MM-DD"
    )
    parser.add_argument(
        "--end", type=validate_date, help="End date in format YYYY-MM-DD"
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=[
            "VolumeReadOps",
            "VolumeTotalReadTime",
            "VolumeWriteOps",
            "VolumeTotalWriteTime",
        ],
        help="List of metrics to fetch",
    )
    parser.add_argument(
        "--style",
        choices=["tsv", "simple", "pretty", "plain", "github", "grid", "fancy"],
        default="simple",
        help="Table style",
    )
    parser.add_argument("--file", action="store_true", help="Output to a file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.volume_id, args.style, args.metrics, args.file, args.start, args.end)
