import boto3
import time
from datetime import datetime
import argparse
from tabulate import tabulate

PAGINATION_COUNT = 300
GET_BATCH_SIZE = 100
PUT_BATCH_SIZE = 20


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
        "--sleep",
        type=int,
        default=1,
        help="The amount of time to sleep in between runs. The default is 60 seconds.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the process the specified number of times, every minute.",
    )
    args = parser.parse_args()

    repeat_count = args.repeat
    sleep_time = args.sleep

    # Print the summary
    print("==========================================")
    print("EBS Custom Metrics Script")
    print(f"Repeat Count: {repeat_count} times")
    print(f"Pagination Count: {PAGINATION_COUNT} items per page")
    print(f"Sleep Time: {sleep_time} seconds")
    print(f"Dry Run: {'Yes' if args.dryrun else 'No'}")
    print("==========================================\n")

    # Create a CloudWatch client
    cloudwatch = boto3.client("cloudwatch")

    # Create an EC2 client
    ec2 = boto3.client("ec2")

    paginator = ec2.get_paginator("describe_volumes")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": PAGINATION_COUNT})

    for i in range(repeat_count):
        start_time = time.time()  # Record the start time of the iteration
        print(
            f"{datetime.now().strftime('%Y-%d-%m %H:%M:%S')} Repeating {i + 1} of {repeat_count} times"
        )

        metric_queries = []
        volume_mapping = {}
        custom_metrics = []
        table = []

        for page in page_iterator:
            for volume in page["Volumes"]:
                volume_id_key = volume.replace("-", "_")
                metric_queries.extend(
                    [
                        {
                            "Id": f"read_time_{volume_id_key}",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EBS",
                                    "MetricName": "VolumeTotalReadTime",
                                    "Dimensions": [
                                        {"Name": "VolumeId", "Value": volume_id_key}
                                    ],
                                },
                                "Period": 60,
                                "Stat": "Sum",
                            },
                        },
                        # ...
                    ]
                )
                volume_mapping[f"read_time_{volume_id_key}"] = volume_id

                if len(metric_queries) == GET_BATCH_SIZE:
                    process_metrics(
                        cloudwatch,
                        metric_queries,
                        table,
                        custom_metrics,
                        args.dryrun,
                        volume_mapping,
                    )
                    metric_queries = []
                    volume_mapping = {}

        # Process remaining metrics
        if metric_queries:
            process_metrics(
                cloudwatch,
                metric_queries,
                table,
                custom_metrics,
                args.dryrun,
                volume_mapping,
            )

        # Publish custom metrics in batches
        if not args.dryrun and custom_metrics:
            for i in range(0, len(custom_metrics), PUT_BATCH_SIZE):
                batch = custom_metrics[i : i + PUT_BATCH_SIZE]
                cloudwatch.put_metric_data(Namespace="Custom_EBS", MetricData=batch)

        # Print the table
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
                    "Total Latency",
                ],
            )
        )
        print("Custom metrics updated for all volumes.")

        end_time = time.time()  # Record the end time of the iteration
        print(f"Run took {end_time - start_time:.2f} seconds")

        if i < repeat_count - 1:
            print(f"Sleeping for {sleep_time} seconds before next iteration:")
            for remaining_seconds in range(sleep_time, 0, -1):
                print(f"\r{remaining_seconds} seconds remaining", end="", flush=True)
                time.sleep(1)
            print("\n")  # Add a newline after the countdown


def process_metrics(
    cloudwatch, metric_queries, table, custom_metrics, dryrun, volume_mapping
):
    response = cloudwatch.get_metric_data(
        MetricDataQueries=metric_queries,
        StartTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)),
        EndTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    for metric_result in response["MetricDataResults"]:
        if metric_result["Values"]:
            volume_id = volume_mapping[metric_result["Id"]]
            if "read_time" in metric_result["Id"]:
                total_read_time = metric_result["Values"][-1]
            elif "read_ops" in metric_result["Id"]:
                read_ops = metric_result["Values"][-1]
            elif "write_time" in metric_result["Id"]:
                total_write_time = metric_result["Values"][-1]
            elif "write_ops" in metric_result["Id"]:
                write_ops = metric_result["Values"][-1]

            # Perform the calculations
            read_latency = (total_read_time / read_ops) * 1000 if read_ops != 0 else 0
            write_latency = (
                (total_write_time / write_ops) * 1000 if write_ops != 0 else 0
            )
            total_latency = read_latency + write_latency

            # Append to the table
            table.append(
                [
                    volume_id,
                    total_read_time,
                    read_ops,
                    read_latency,
                    total_write_time,
                    write_ops,
                    write_latency,
                    total_latency,
                ]
            )

            # Append to custom metrics if not in dry run mode
            if not dryrun:
                custom_metrics.extend(
                    [
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
                    ]
                )


if __name__ == "__main__":
    main()
