# EBS Latency Custom Metrics

This project consists of a Lambda function and a Terraform script that work together to calculate and publish custom Amazon Elastic Block Store (EBS) read and write latency metrics to Amazon CloudWatch.

## Overview

The Lambda function (`ebs-lambda-cw-custom-metric-latency.py`) retrieves EBS volume metrics, including total read time, read operations, total write time, and write operations. It then calculates the read and write latencies and publishes them as custom CloudWatch metrics.

The Terraform script (`main.tf`) automates the deployment of the Lambda function and schedules its execution using Amazon EventBridge. It also sets up the necessary IAM roles and permissions.

## Requirements

- AWS CLI configured with the appropriate AWS credentials.
- Python 3.8 or higher for the Lambda function.
- Terraform v0.12 or higher.
- An S3 bucket to store the Terraform state (optional).

## Configuration

### Lambda Function

The Lambda function takes the following environment variables:

- `PAGINATION_COUNT`: The number of EBS volumes to process in each pagination call (default is 300).
- `TIME_INTERVAL`: The time interval, in seconds, to look back for metric data (calculated from the EventBridge schedule rate).

### Terraform Script

The Terraform script (`main.tf`) uses the following variables:

- `region`: The AWS region (default is "us-west-2").
- `profile`: The AWS profile (default is "hme").
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
