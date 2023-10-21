# EBS Latency Custom Metrics

This folder consists of a Lambda function and a Terraform script that work together to calculate and publish custom Amazon Elastic Block Store (EBS) read and write latency metrics to Amazon CloudWatch.

## Overview

The Lambda function (`ebs-lambda-cw-custom-metric-latency.py`) retrieves EBS volume metrics, including total read time, read operations, total write time, and write operations. It then calculates the read and write latencies and publishes them as custom CloudWatch metrics using these forumulas:

_Write Latency (VolumeWriteLatency)_ = `(Total Write Time / Write Operations) * 1000`
_Read Latency (VolumeReadLatency)_ = `(Total Read Time / Read Operations) * 1000`
_Total Latency (VolumeTotalLatency)_ = `Write Latency + Read Latency`

In this script the CloudWatch metrics are published to the `Custom_EBS` namespace.

The Terraform script (`main.tf`) automates the deployment of the Lambda function and schedules its execution using Amazon EventBridge. It also sets up the necessary IAM roles and permissions.

## Requirements

- AWS CLI configured with the appropriate AWS credentials.
- Python 3.8 or higher for the Lambda function.
- Terraform v0.12 or higher.

## Configuration

You will make changes to the Terraform script to adjust the Lambda function configuration and schedule. The Lambda function code itself can be modified as needed, such as changing the CloudWatch namespace, logging level, etc.

To change things like the CloudWatch Namespace and Metric Names, you will look at the Python code.

### Lambda Function

Adjust these OS Environment variables in the `main.tf` script to be used in the Lambda function:

- `PAGINATION_COUNT` - Number of volumes to retrieve from AWS API call. Default is 300.
- `TIME_INTERVAL` - Time interval in seconds to collect the metric data. Default is 60 (1 minute) since EBS metrics are gathered per minute.
- `GET_BATCH_SIZE` - The API batch size for retrieving volume metrics from CloudWatch. Default is 500.
- `PUT_BATCH_SIZE` - The API batch size for publishing custom metrics to CloudWatch. Default is 1000.
- `LOGGING_LEVEL` - Logging level for the Lambda function. Default is "INFO".

### Terraform Script

The Terraform script (`main.tf`) uses the following variables:

- `region`: The AWS region to deploy to.
- `profile`: The AWS profile to use
- `schedule_rate`: The frequency of the EventBridge schedule in minutes (default is 1).

## Deployment

1. Zip the Lambda function:

```bash
zip ebs-lambda-cw-custom-metric-latency.zip ebs-lambda-cw-custom-metric-latency.py
```

2. Initialize Terraform:

```bash
terraform init
```

3. Plan the Terraform changes:

```bash
terraform plan
```

4. Apply the Terraform changes:

```bash
terraform apply
```

## Adapting to a Different Environment

To run this in a different environment, you may need to adjust the following:

- Modify the AWS region and profile in the Terraform variables.
- Adjust the `PAGINATION_COUNT` and `schedule_rate` as needed.
- Ensure that the Lambda execution role has the necessary permissions for CloudWatch (`cloudwatch:PutMetricData`) and EC2 (`ec2:DescribeVolumes`).

## Troubleshooting

Ensure that the IAM role associated with the Lambda function has the required permissions. If you encounter an `AccessDenied` error related to `cloudwatch:PutMetricData`, verify the IAM policy defined in the Terraform script.

## TODO

- Make the Metric Namespace and Metric Names onfigurable via variables or parameters. Currently they are hardcoded in the Python code.
- Add try / catch logics to handle any exceptions gracefully.
