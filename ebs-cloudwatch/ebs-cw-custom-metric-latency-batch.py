import boto3
import time
import logging
from datetime import datetime
import argparse

PAGINATION_COUNT = 300
TIME_INTERVAL = 60
GET_BATCH_SIZE = 500
PUT_BATCH_SIZE = 1000
CW_CUSTOM_NAMESPACE = "Custom_EBS"


def main():
    """
    Entry point of the script. This function handles command-line arguments and orchestrates the
    calculation and publication of custom EBS metrics.
    Command-line Arguments:
        --repeat: Number of times to repeat the process. Default is 1.
        --sleep: Number of seconds to sleep between repeats. Default is 5.
        --validate: Validate that custom metrics are published to CloudWatch.
        --verbose: Enable verbose logging for debugging.
    """
    args = parse_args()
    setup_logging(args.verbose)

    repeat_count = args.repeat
    sleep_time = args.sleep
    validate = args.validate

    overall_success = True

    overall_validate_success_count = 0  # Counter for successfully validated metrics
    overall_validate_failure_count = 0  # Counter for failed validations

    for i in range(repeat_count):
        cycle_count = i + 1
        print(
            f"Repeating {cycle_count} of {repeat_count} times at {datetime.now().strftime('%Y-%d-%m %H:%M:%S')}"
        )

        start_time = time.time()  # Record the start time

        try:
            (
                volumes_processed,
                volumes_with_metrics,
                volumes_without_metrics,
                validate_success_count,
                validate_failure_count,
            ) = run_custom_metrics_batch(validate)
            overall_validate_success_count += validate_success_count
            overall_validate_failure_count += validate_failure_count
        except Exception as e:
            logging.error(f"Error occurred during cycle {cycle_count}: {e}")
            overall_success = False
            continue

        end_time = time.time()  # Record the end time

        total_time_taken = end_time - start_time  # Calculate total time taken
        repeat_final_message = (
            f"Processed {volumes_processed} volumes in {total_time_taken:.2f} seconds. "
            f"{volumes_with_metrics} volumes have CW metrics. {volumes_without_metrics} did not have CW metrics."
        )
        logging.info(repeat_final_message)

        print(repeat_final_message)

        # Sleep and show the countdown if this is not the last iteration
        if i < repeat_count - 1:
            for j in range(sleep_time, 0, -1):
                print(
                    f"\rSleeping for {str(j).zfill(len(str(sleep_time)))} seconds... Ran {cycle_count} of {repeat_count} times.",
                    end="",
                    flush=True,
                )
                time.sleep(1)
            print("\rContinuing...                    ")

    if overall_success:
        print("Script executed successfully.")
    else:
        print("Script encountered errors.")

    if validate:
        print(
            f"Validation succeeded for {validate_success_count} metrics and failed for {validate_failure_count} metrics."
        )


def run_custom_metrics_batch(validate):
    """
    Calculates and publishes custom EBS metrics in batch mode.
    Parameters:
        validate (bool): Whether to validate that metrics are successfully published.
    Returns:
        tuple: A tuple containing various metrics and validation counts.
    """

    logging.info("Starting custom EBS metrics calculation in batch mode.")

    cloudwatch, ec2 = initialize_aws_services()

    paginator = ec2.get_paginator("describe_volumes")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": PAGINATION_COUNT})

    metric_queries = []
    custom_metrics = []

    volumes_processed = 0
    volumes_with_metrics = 0
    volumes_without_metrics = 0
    validate_success_count = 0
    validate_failure_count = 0

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
        cloudwatch.put_metric_data(Namespace=CW_CUSTOM_NAMESPACE, MetricData=batch)

        if validate:
            if validate_custom_metrics(cloudwatch, batch):
                validate_success_count += len(batch)
            else:
                validate_failure_count += len(batch)

    logging.info("Custom metrics updated for all volumes in batch mode.")

    return (
        volumes_processed,
        volumes_with_metrics,
        volumes_without_metrics,
        validate_success_count,
        validate_failure_count,
    )


def process_metrics(cloudwatch, metric_queries, custom_metrics):
    """
    Processes the metrics queries to calculate custom metrics.
    Parameters:
        cloudwatch (boto3.client): CloudWatch client.
        metric_queries (list): List of metric queries.
        custom_metrics (list): List to store calculated custom metrics.
    Returns:
        tuple: A tuple containing counts of volumes with and without metrics.
    """
    volumes_with_metrics = 0
    volumes_without_metrics = 0

    try:
        response = cloudwatch.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - TIME_INTERVAL)
            ),
            EndTime=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
    except Exception as e:
        logging.error(f"Error getting metric data: {e}")
        raise

    if not response or "MetricDataResults" not in response:
        logging.error("No metric data returned from CloudWatch")
        raise ValueError(
            "Invalide API response or no metric data returned from CloudWatch"
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


def validate_custom_metrics(cloudwatch, custom_metrics_batch, verbose=False):
    retry_count = 10
    delay = 1
    while retry_count > 0:
        metric_names_sent = set(metric["MetricName"] for metric in custom_metrics_batch)
        metrics_received = cloudwatch.list_metrics(Namespace=CW_CUSTOM_NAMESPACE)
        metric_names_received = set(
            metric["MetricName"] for metric in metrics_received.get("Metrics", [])
        )
        missing_metrics = metric_names_sent - metric_names_received

        if verbose:
            logging.debug(f"Sent Metrics: {metric_names_sent}")
            logging.debug(f"Received Metrics: {metric_names_received}")
            logging.debug(f"Missing Metrics: {missing_metrics}")

        if missing_metrics:
            logging.warning(
                f"Metrics not found on attempt, retrying: {missing_metrics}"
            )
            time.sleep(delay)
            retry_count -= 1
        else:
            return True

    logging.error("Failed to validate metrics after 10 retries.")
    return False


def initialize_aws_services():
    try:
        cloudwatch = boto3.client("cloudwatch")
        ec2 = boto3.client("ec2")
        return cloudwatch, ec2
    except Exception as e:
        logging.error(f"Failed to initialize AWS services: {e}")
        raise


def setup_logging(verbose):
    """
    Sets up logging.
    Parameters:
        verbose (bool): Whether to enable verbose logging.
    """
    logging_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=logging_level)


def parse_args():
    """
    Parses command-line arguments.
    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
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
        "--validate",
        action="store_true",
        help="Validate that the custom metrics are published to CloudWatch.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging for debugging."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
