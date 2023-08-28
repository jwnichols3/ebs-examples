import boto3
import time
import logging
from datetime import datetime
import argparse

PAGINATION_COUNT = 300
TIME_INTERVAL = 60
GET_BATCH_SIZE = 500
PUT_BATCH_SIZE = 1000


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

        start_time = time.time()  # Record the start time

        (
            volumes_processed,
            volumes_with_metrics,
            volumes_without_metrics,
        ) = run_custom_metrics_batch()

        end_time = time.time()  # Record the end time

        total_time_taken = end_time - start_time  # Calculate total time taken
        final_message = (
            f"Processed {volumes_processed} volumes in {total_time_taken:.2f} seconds. "
            f"{volumes_with_metrics} volumes have CW metrics. {volumes_without_metrics} did not have CW metrics."
        )
        logging.info(final_message)

        print(final_message)

        # Sleep and show the countdown if this is not the last iteration
        if i < repeat_count - 1:
            for i in range(sleep_time, 0, -1):
                print(
                    f"\rSleeping for {str(i).zfill(len(str(sleep_time)))} seconds...",
                    end="",
                    flush=True,
                )
                time.sleep(1)
            print("\rContinuing...                    ")


def run_custom_metrics_batch():
    logging.info("Starting custom EBS metrics calculation in batch mode.")

    cloudwatch = boto3.client("cloudwatch")
    ec2 = boto3.client("ec2")

    paginator = ec2.get_paginator("describe_volumes")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": PAGINATION_COUNT})

    metric_queries = []
    custom_metrics = []

    volumes_processed = 0
    volumes_with_metrics = 0
    volumes_without_metrics = 0

    for page in page_iterator:
        for volume in page["Volumes"]:
            volumes_processed += 1
            volume_id = volume["VolumeId"]
            safe_volume_id = volume_id.replace("-", "_")

            # Add the metric queries for this volume
            metric_queries.extend(
                [
                    # Read metrics
                    {
                        "Id": f"read_time_{safe_volume_id}",
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
                        "Id": f"read_ops_{safe_volume_id}",
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
                        "Id": f"write_time_{safe_volume_id}",
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
                        "Id": f"write_ops_{safe_volume_id}",
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
                ]
            )

            # Process in batches
            if len(metric_queries) == GET_BATCH_SIZE:
                new_volumes_with_metrics, new_volumes_without_metrics = process_metrics(
                    cloudwatch, metric_queries, custom_metrics
                )

                volumes_with_metrics += new_volumes_with_metrics
                volumes_without_metrics += new_volumes_without_metrics
                metric_queries = []

    # Process remaining metrics
    if metric_queries:
        new_volumes_with_metrics, new_volumes_without_metrics = process_metrics(
            cloudwatch, metric_queries, custom_metrics
        )
        volumes_with_metrics += new_volumes_with_metrics
        volumes_without_metrics += new_volumes_without_metrics

    # Publish custom metrics in batches
    for i in range(0, len(custom_metrics), PUT_BATCH_SIZE):
        batch = custom_metrics[i : i + PUT_BATCH_SIZE]
        cloudwatch.put_metric_data(Namespace="Custom_EBS", MetricData=batch)

    logging.info("Custom metrics updated for all volumes in batch mode.")

    return volumes_processed, volumes_with_metrics, volumes_without_metrics


def process_metrics(cloudwatch, metric_queries, custom_metrics):
    volumes_with_metrics = 0
    volumes_without_metrics = 0

    response = cloudwatch.get_metric_data(
        MetricDataQueries=metric_queries,
        StartTime=time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - TIME_INTERVAL)
        ),
        EndTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    logging.debug("Response for get_metric_data is %s", response)

    # Process the response and update custom_metrics
    for i in range(0, len(response["MetricDataResults"]), 4):
        # Check if the Values list has data for each metric
        if all(response["MetricDataResults"][j]["Values"] for j in range(i, i + 4)):
            total_read_time = response["MetricDataResults"][i]["Values"][-1]
            read_ops = response["MetricDataResults"][i + 1]["Values"][-1]
            total_write_time = response["MetricDataResults"][i + 2]["Values"][-1]
            write_ops = response["MetricDataResults"][i + 3]["Values"][-1]
            volumes_with_metrics += 1

        else:
            logging.warning(
                f"Metrics data missing for volume with ID derived from {metric_queries[i]['Id']}"
            )
            volumes_without_metrics += 1
            continue

        # Perform the calculations
        read_latency = (total_read_time / read_ops) * 1000 if read_ops != 0 else 0
        write_latency = (total_write_time / write_ops) * 1000 if write_ops != 0 else 0
        total_latency = read_latency + write_latency

        # Extract volume_id from the query
        # volume_id = metric_queries[i]["MetricStat"]["Metric"]["Dimensions"][0]["Value"]
        # volume_id = metric_queries[i]["Id"].split("_")[-1]
        safe_volume_id = metric_queries[i]["Id"].split("_", 2)[-1]
        volume_id = safe_volume_id.replace("_", "-")

        # Add to custom_metrics
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

        logging.info(
            f"Latency metrics updated for volume {volume_id}: "
            f"Read L = {read_latency:.2f} ms "
            f"(Rt {total_read_time:.2f} / Rops {read_ops:.2f}), "
            f"Write L = {write_latency:.2f} ms "
            f"(Wt {total_write_time:.2f} / Wops {read_ops:.2f}), "
            f"Total L = {total_latency:.2f} ms {read_latency:.2f}+{write_latency:.2f}"
        )

    return volumes_with_metrics, volumes_without_metrics


if __name__ == "__main__":
    main()
