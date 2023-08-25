import boto3
import time
import logging
from datetime import datetime
import argparse

PAGINATION_COUNT = 300
TIME_INTERVAL = 60


def main():
    parser = argparse.ArgumentParser(
        description="Calculate and publish custom EBS metrics."
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the process the specified number of times. Default is 1.",
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=5,
        help="Sleep for the specified number of seconds between repeats. Default is 5 seconds.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging for debugging."
    )
    args = parser.parse_args()

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level)

    repeat_count = args.repeat
    sleep_time = args.sleep

    for i in range(repeat_count):
        print(
            f"Repeating {i + 1} of {repeat_count} times at {datetime.now().strftime('%Y-%d-%m %H:%M:%S')}"
        )
        run_custom_metrics()

        if i < repeat_count - 1:
            print(f"Sleeping for {sleep_time} seconds before next iteration:")
            for remaining_seconds in range(sleep_time, 0, -1):
                print(f"\r{remaining_seconds} seconds remaining", end="", flush=True)
                time.sleep(1)
            print("\n")


def run_custom_metrics():
    logging.info(
        f"Starting custom EBS metrics calculation. PAGINATION_COUNT: {PAGINATION_COUNT}"
    )

    cloudwatch = boto3.client("cloudwatch")
    ec2 = boto3.client("ec2")

    paginator = ec2.get_paginator("describe_volumes")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": PAGINATION_COUNT})

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
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - TIME_INTERVAL)
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

                total_latency = read_latency + write_latency

                # Publish the custom metrics
                cloudwatch.put_metric_data(
                    Namespace="Custom_EBS",
                    MetricData=[
                        {
                            "MetricName": "VolumeReadLatency",
                            "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                            "Value": read_latency,
                        },
                        {
                            "MetricName": "VolumeWriteLatency",
                            "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                            "Value": write_latency,
                        },
                        {
                            "MetricName": "VolumeTotalLatency",
                            "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                            "Value": total_latency,
                        },
                    ],
                )
                logging.info(
                    f"Metrics updated for volume {volume_id}: "
                    f"Read Latency = {read_latency:.2f} ms, "
                    f"Write Latency = {write_latency:.2f} ms, "
                    f"Total Latency = {total_latency:.2f} ms."
                )

    logging.info("Custom metrics updated for all volumes.")


if __name__ == "__main__":
    main()
