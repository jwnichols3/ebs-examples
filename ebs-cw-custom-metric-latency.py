import boto3
import time
from datetime import datetime
import argparse
from tabulate import tabulate

PAGINATION_COUNT = 5
SLEEP_TIME = 5


def main():
    parser = argparse.ArgumentParser(
        description="Calculate and publish custom EBS metrics."
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Print the calculated values without publishing them.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the process the specified number of times, every minute.",
    )
    args = parser.parse_args()

    repeat_count = args.repeat

    # Print the summary
    print("==========================================")
    print("EBS Custom Metrics Script")
    print(f"Repeat Count: {repeat_count} times")
    print(f"Pagination Count: {PAGINATION_COUNT} items per page")
    print(f"Dry Run: {'Yes' if args.dryrun else 'No'}")
    print("==========================================\n")

    for i in range(repeat_count):
        start_time = time.time()  # Record the start time of the iteration
        print(
            f"{datetime.now().strftime('%Y-%d-%m %H:%M:%S')} Repeating {i + 1} of {repeat_count} times"
        )

        # Create a CloudWatch client
        cloudwatch = boto3.client("cloudwatch")

        # Create an EC2 client
        ec2 = boto3.client("ec2")

        # Create a table for dry run output
        table = []

        paginator = ec2.get_paginator("describe_volumes")
        page_iterator = paginator.paginate(
            PaginationConfig={"PageSize": PAGINATION_COUNT}
        )

        # Iterate over all volumes
        for page in page_iterator:
            for volume in page["Volumes"]:
                volume_id = volume["VolumeId"]

                # Query the necessary metrics for this volume
                response = cloudwatch.get_metric_data(
                    MetricDataQueries=[
                        # Read metrics
                        {
                            "Id": "read_time",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EBS",
                                    "MetricName": "VolumeTotalReadTime",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                },
                                "Period": 60,
                                "Stat": "Sum",
                            },
                        },
                        {
                            "Id": "read_ops",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EBS",
                                    "MetricName": "VolumeReadOps",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                },
                                "Period": 60,
                                "Stat": "Sum",
                            },
                        },
                        # Write metrics
                        {
                            "Id": "write_time",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EBS",
                                    "MetricName": "VolumeTotalWriteTime",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                },
                                "Period": 60,
                                "Stat": "Sum",
                            },
                        },
                        {
                            "Id": "write_ops",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EBS",
                                    "MetricName": "VolumeWriteOps",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                },
                                "Period": 60,
                                "Stat": "Sum",
                            },
                        },
                    ],
                    StartTime=time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)
                    ),
                    EndTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )

                if (
                    response["MetricDataResults"]
                    and response["MetricDataResults"][0]["Values"]
                ):
                    # Extract the values
                    total_read_time = response["MetricDataResults"][0]["Values"][-1]
                    read_ops = response["MetricDataResults"][1]["Values"][-1]
                    total_write_time = response["MetricDataResults"][2]["Values"][-1]
                    write_ops = response["MetricDataResults"][3]["Values"][-1]

                    # Perform the calculations
                    read_latency = (
                        (total_read_time / read_ops) * 1000 if read_ops != 0 else 0
                    )
                    write_latency = (
                        (total_write_time / write_ops) * 1000 if write_ops != 0 else 0
                    )

                    table.append(
                        [
                            volume_id,
                            total_read_time,
                            read_ops,
                            read_latency,
                            total_write_time,
                            write_ops,
                            write_latency,
                        ]
                    )
                    if not args.dryrun:
                        # Publish the custom metrics
                        cloudwatch.put_metric_data(
                            Namespace="Custom_EBS",
                            MetricData=[
                                {
                                    "MetricName": "VolumeReadLatency",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                    "Value": read_latency,
                                },
                                {
                                    "MetricName": "VolumeWriteLatency",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id}
                                    ],
                                    "Value": write_latency,
                                },
                            ],
                        )
                else:
                    print(f"No data available for volume {volume_id}. Skipping.")
                    continue

        print(
            tabulate(
                table,
                headers=[
                    "Volume ID",
                    "Total Read Time",
                    "Read Ops",
                    "Read Latency",
                    "Total Write Time",
                    "Write Ops",
                    "Write Latency",
                ],
            )
        )
        print("Custom metrics updated for all volumes.")

        end_time = time.time()  # Record the end time of the iteration
        print(f"Run took {end_time - start_time:.2f} seconds")

        if i < repeat_count - 1:
            print(f"Sleeping for {SLEEP_TIME} seconds before next iteration:")
            for remaining_seconds in range(SLEEP_TIME, 0, -1):
                print(f"\r{remaining_seconds} seconds remaining", end="", flush=True)
                time.sleep(1)
            print("\n")  # Add a newline after the countdown


if __name__ == "__main__":
    main()
