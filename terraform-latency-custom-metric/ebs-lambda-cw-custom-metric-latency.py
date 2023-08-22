import boto3
import os
import time
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Read PAGINATION_COUNT and TIME_INTERVAL from environment variables
PAGINATION_COUNT = int(os.environ.get("PAGINATION_COUNT", 300))
TIME_INTERVAL = int(os.environ.get("TIME_INTERVAL", 60))


def lambda_handler(event, context):
    logger.info(
        f"Starting custom EBS metrics calculation. PAGINATION_COUNT: {PAGINATION_COUNT}"
    )

    # Create a CloudWatch client
    cloudwatch = boto3.client("cloudwatch")

    # Create an EC2 client
    ec2 = boto3.client("ec2")

    paginator = ec2.get_paginator("describe_volumes")
    page_iterator = paginator.paginate(PaginationConfig={"PageSize": PAGINATION_COUNT})

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
                    ],
                )
                # logger.info(f"Metrics updated for volume {volume_id}.")

    logger.info("Custom metrics updated for all volumes.")
