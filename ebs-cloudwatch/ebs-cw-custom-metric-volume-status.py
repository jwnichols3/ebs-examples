import time
import logging
from datetime import datetime
import argparse
from tabulate import tabulate
​
​
class Config:
    PAGINATION_COUNT = 300
    TIME_INTERVAL = 60
    GET_BATCH_SIZE = 500
    PUT_BATCH_SIZE = 1000
    CW_CUSTOM_NAMESPACE = "Custom_EBS"
​
​
def main():
    """
    Entry point of the script. This function handles command-line arguments and orchestrates the
    calculation and publication of custom EBS metrics.
    Command-line Arguments:
        --repeat: Number of times to repeat the process. Default is 1.
        --sleep: Number of seconds to sleep between repeats. Default is 5.
        --validate: Validate that custom metrics are published to CloudWatch.
        --verbose: Enable verbose logging for debugging.
        --print: Print out a table of the EBS volume metrics.
    """
    args = parse_args()
    setup_logging(args.verbose)
​
    repeat_count = args.repeat
    sleep_time = args.sleep
    validate = args.validate
    print_table = args.print
​
    overall_success = True
​
    overall_validate_success_count = 0  # Counter for successfully validated metrics
    overall_validate_failure_count = 0  # Counter for failed validations
​
    for i in range(repeat_count):
        cycle_count = i + 1
        print(
            f"Repeating {cycle_count} of {repeat_count} times at {datetime.now().strftime('%Y-%d-%m %H:%M:%S')}"
        )
​
        start_time = time.time()  # Record the start time
​
        try:
            (
                volumes_processed,
                validate_success_count,
                validate_failure_count,
                metrics_table,
            ) = run_custom_metrics_batch(validate)
            overall_validate_success_count += validate_success_count
            overall_validate_failure_count += validate_failure_count
        except Exception as e:
            logging.error(f"Error occurred during cycle {cycle_count}: {e}")
            overall_success = False
            continue
​
        end_time = time.time()  # Record the end time
​
        total_time_taken = end_time - start_time  # Calculate total time taken
        repeat_final_message = (
            f"Processed {volumes_processed} volumes in {total_time_taken:.2f} seconds."
        )
        logging.info(repeat_final_message)
​
        print(repeat_final_message)
​
        # Print the table if the --print option is used
        if print_table:
            print("\nEBS Volume Metrics by Region:")
            print(tabulate(metrics_table, headers="keys", tablefmt="grid"))
​
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
​
    if overall_success:
        print("Script executed successfully.")
    else:
        print("Script encountered errors.")
​
    if validate:
        print(
            f"Validation succeeded for {overall_validate_success_count} metrics and failed for {overall_validate_failure_count} metrics."
        )
​
​
def run_custom_metrics_batch(validate):
    """
    Calculates and publishes custom EBS volume metrics in batch mode.
    Parameters:
        validate (bool): Whether to validate that metrics are successfully published.
    Returns:
        tuple: A tuple containing various metrics and validation counts.
    """
    logging.info("Starting custom EBS volume metrics calculation in batch mode.")
​
    cloudwatch, ec2 = initialize_aws_services()
​
    regions = [region["RegionName"] for region in ec2.describe_regions()["Regions"]]
    metric_data = []
    metrics_table = []
​
    volumes_processed = 0
    validate_success_count = 0
    validate_failure_count = 0
​
    for region in regions:
        ec2_region = boto3.client("ec2", region_name=region)
        paginator = ec2_region.get_paginator("describe_volumes")
        page_iterator = paginator.paginate(
            PaginationConfig={"PageSize": Config.PAGINATION_COUNT}
        )
​
        total_volumes = 0
        attached_volumes = 0
        unattached_volumes = 0
​
        for page in page_iterator:
            for volume in page["Volumes"]:
                volumes_processed += 1
                total_volumes += 1
                if volume["Attachments"]:
                    attached_volumes += 1
                else:
                    unattached_volumes += 1
​
        metric_data.extend(
            [
                {
                    "MetricName": "TotalVolumes",
                    "Dimensions": [{"Name": "Region", "Value": region}],
                    "Value": total_volumes,
                    "Unit": "Count",
                },
                {
                    "MetricName": "AttachedVolumes",
                    "Dimensions": [{"Name": "Region", "Value": region}],
                    "Value": attached_volumes,
                    "Unit": "Count",
                },
                {
                    "MetricName": "UnattachedVolumes",
                    "Dimensions": [{"Name": "Region", "Value": region}],
                    "Value": unattached_volumes,
                    "Unit": "Count",
                },
            ]
        )
​
        metrics_table.append(
            {
                "Region": region,
                "Total": total_volumes,
                "Attached": attached_volumes,
                "Unattached": unattached_volumes,
            }
        )
​
    # Publish custom metrics in batches
    for i in range(0, len(metric_data), Config.PUT_BATCH_SIZE):
        batch = metric_data[i : i + Config.PUT_BATCH_SIZE]
        cloudwatch.put_metric_data(
            Namespace=Config.CW_CUSTOM_NAMESPACE, MetricData=batch
        )
​
        if validate:
            if validate_custom_metrics(cloudwatch, batch):
                validate_success_count += len(batch)
            else:
                validate_failure_count += len(batch)
​
    logging.info("Custom volume metrics updated for all regions in batch mode.")
​
    return (
        volumes_processed,
        validate_success_count,
        validate_failure_count,
        metrics_table,
    )
​
​
def validate_custom_metrics(cloudwatch, custom_metrics_batch, verbose=False):
    retry_count = 10
    delay = 1
    while retry_count > 0:
        metric_names_sent = set(metric["MetricName"] for metric in custom_metrics_batch)
        metrics_received = cloudwatch.list_metrics(Namespace=Config.CW_CUSTOM_NAMESPACE)
        metric_names_received = set(
            metric["MetricName"] for metric in metrics_received.get("Metrics", [])
        )
        missing_metrics = metric_names_sent - metric_names_received
​
        if verbose:
            logging.debug(f"Sent Metrics: {metric_names_sent}")
            logging.debug(f"Received Metrics: {metric_names_received}")
            logging.debug(f"Missing Metrics: {missing_metrics}")
​
        if missing_metrics:
            logging.warning(
                f"Metrics not found on attempt, retrying: {missing_metrics}"
            )
            time.sleep(delay)
            retry_count -= 1
        else:
            return True
​
    logging.error("Failed to validate metrics after 10 retries.")
    return False
​
​
def initialize_aws_services():
    try:
        cloudwatch = boto3.client("cloudwatch")
        ec2 = boto3.client("ec2")
        return cloudwatch, ec2
    except Exception as e:
        logging.error(f"Failed to initialize AWS services: {e}")
        raise
​
​
def setup_logging(verbose):
    """
    Sets up logging.
    Parameters:
        verbose (bool): Whether to enable verbose logging.
    """
    logging_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=logging_level)
​
​
def parse_args():
    """
    Parses command-line arguments.
    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Calculate and publish custom EBS volume metrics."
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
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print out a table of the EBS volume metrics.",
    )
    return parser.parse_args()
​
​
if __name__ == "__main__":
    main()