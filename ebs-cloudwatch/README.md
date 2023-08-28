# ebs-examples

# Overview

This folder contains the stand-alone Python scripts to update CloudWatch Alarms, show if any EBS volumes are in the Impaired status, show latency metrics, create custom CloudWatch metrics for read and write latency, example CloudWatch dashboards, and more.

# Disclaimer

Please note: These scripts are intended for educational purposes and are not recommended for production use. Always test scripts in a controlled environment before using them in a production capacity. There is minimum error handling implemented and not all scenarious are accounted for such as scale, access controls, and input validation. There is an inherent assumption that you have a way to run these scripts on a system that has access to the AWS account in question and the required privileges.

# Python Scripts

These are the Python scripts included in this repository. More details of each script are provided below.

`ebs-cw-alarm-impairedvol.py`

This Python script creates AWS CloudWatch Alarms for Amazon EBS volumes. These alarms are designed to alert when an EBS volume becomes "impaired." A "impaired" volume is one that has a queue length but no read or write operations.

`ebs-cw-dashboard-latency.py`

This Python script creates a CloudWatch Dashboard named "Read and Write Latency". The dashboard includes two calculated metrics for every EBS volume in the AWS Account.

`ebs-cw-show-detailed-metrics-for-latency-by-vol.py`

This Python script displays detailed CloudWatch metrics for read, write, and overall latency for each EBS volume in the AWS account. It calculates and prints these metrics for each volume for a given time frame (defaulting in the last 24 hours). This provides visibility into the latency performance of each EBS volume over time. You can use this with the `--style` option of `tvs` to output in a tabular format for easy importing into spreadsheets or other tools.

`ebs-cw-show-latency-metrics-current.py`

This Python script calculates and displays the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

`ebs-cw-show-impairedvol.py`

This Python script monitors the I/O operations for Amazon EBS volumes in an AWS account and creates CloudWatch Alarms for "impaired" volumes. A "impaired" volume is one that has a queue length but no read or write operations.

## ebs-cw-alarm-impairedvol.py

EBS Impaired Volume CloudWatch Alarm Script

This Python script uses the AWS SDK (boto3) to create AWS CloudWatch Alarms for Amazon EBS volumes. The purpose of these alarms is to alert when EBS volumes become "impaired," or unresponsive. The script provides options to create alarms for a specific volume, for all volumes, or to clean up alarms for volumes that no longer exist.

The Alert name has a pattern `ImpairedVol_{volume-id}`

Change the `SNS_ALARM_ACTION_ARN` variable to an SNS topic ARN to send alarm notifications.

### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Argparse

### Python Module Installation

Ensure that you have Python 3.6+ installed, along with Boto3 and Argparse. You can install Boto3 with pip:

`pip install boto3`
`pip install argparse`

Then, download the Python script `ebs-cw-alarm-impairedvol.py`.

### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:PutMetricAlarm`: This permission is required to create a new alarm.
- `cloudwatch:DeleteAlarms`: This permission is required to delete alarms.
- `cloudwatch:DescribeAlarms`: This permission is required to retrieve information about the current alarms.

_EC2 Permissions_

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

SNS Permissions:

- `sns:GetTopicAttributes`: This permission is required to retrieve the attributes of the SNS topic.
- `sns:ListTopics`: This permission is required to list all the SNS topics in your AWS account.

### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-alarm-impairedvol.py [arguments]`

### Arguments

- `--volumeid`: Specify the ID of a new EBS volume to create an alarm for.
- `--verbose`: Enable verbose output.
- `--impaired-alarm-for-all-volumes`: Create impaired volume alarms for all EBS volumes.
- `--impaired-alarm-cleanup`: Remove impaired volume alarms for non-existent volumes.
- `--all`: Perform all operations: add impaired volume alarms for all volumes and remove alarms for non-existent volumes.

If the script is run without any arguments, it will display help output.

### Examples

To create a impaired volume alarm for a specific EBS volume:

`python ebs-cw-alarm-impairedvol.py --volumeid vol-0abcdefgh123`

To create impaired volume alarms for all EBS volumes and to remove alarms for volumes that no longer exist:

`python ebs-cw-alarm-impairedvol.py --all`

## ebs-cw-dashboard-latency.py

EBS CloudWatch Dashboard Latency Script

This Python script uses the AWS SDK (boto3) to create a CloudWatch Dashboard named "Read and Write Latency". The dashboard includes two calculated metrics for every EBS volume in the AWS Account: EBS Write Latency and EBS Read Latency. The script ensures that the metrics are only created if they don't already exist.

### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Argparse
- AWS credentials configured (can be configured using the AWS CLI)

### Python Module Installation

1. Make sure that you have Python 3.6 or newer installed.
2. Install Boto3 using pip (`pip install boto3 argparse`).
3. Download the Python script "ebs-cw-dashboard-latency.py".

### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:PutDashboard`: This permission is required to create or modify dashboards in CloudWatch.
- `cloudwatch:DeleteDashboards`: This permission is required to delete dashboards.
- `cloudwatch:ListMetrics`: This permission is required to retrieve a list of the current metrics.
- `cloudwatch:GetDashboard`: This permission is required to retrieve information about specific dashboards.
- `cloudwatch:DescribeAlarmHistory`: This permission is required to retrieve the history of a specific alarm.

EC2 Permissions

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-dashboard-latency.py [arguments]`

### Arguments

- `--verbose`: If this argument is supplied, the script will output debug statements.
- `--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

### Examples

To run the script with verbose output:

`python ebs-cw-dashboard-latency.py --verbose`

To see what the dashboard JSON would look like without actually creating the dashboard:

`python ebs-cw-dashboard-latency.py --dry-run`

## ebs-cw-show-latency-metrics-current.py

EBS CloudWatch Show Latency Script

This Python script uses the AWS SDK (boto3) to calculate and display the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Tabulate and Argparse
- AWS credentials configured (can be configured using the AWS CLI)

### Python Module Installation

- Ensure that you have Python 3.6 or newer installed.
- Install Boto3, tabulate, and argparse using pip (pip install boto3 tabulate argparse).
- Download the Python script "ebs-cw-show-latency-metrics-current.py".

### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:GetMetricStatistics`: This permission is required to retrieve statistical data for a specified metric.
- `cloudwatch:ListMetrics`: This permission is required to retrieve a list of the current metrics.

_EC2 Permissions_

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-show-latency-metrics-current.py [arguments]`

### Arguments

- `--volume-id VOL_ID`: If this argument is supplied, the script will calculate the latency for the specified volume ID only. Otherwise, it calculates latency for all volumes.
- `--verbose`: If this argument is supplied, the script will output additional information.
- `--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

### Examples

To run the script for a specific volume with verbose output:

`python ebs-cw-show-latency-metrics-current.py --volume-id vol-0123456789abcdef0 --verbose`

To run the script for all volumes:

`python ebs-cw-show-latency-metrics-current.py`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.

## ebs-cw-show-impairedvol.py

EBS CloudWatch Show Impaired Volumes Script.

This script is a Python program that uses the AWS SDK (boto3) to monitor the I/O operations for Amazon EBS volumes in an AWS account and create CloudWatch Alarms for "impaired" volumes. A "impaired" volume is one that has a queue length but no read or write operations.

### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Argparse
- AWS credentials configured (can be configured using the AWS CLI)

### Python Module Installation

- Ensure that you have Python 3.6 or newer installed.
- Install Boto3 and Argepars using pip (pip install boto3 argparse).
- Download the Python script "ebs-cw-show-impairedvol.py".

### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:DescribeAlarms`: This permission is required to retrieve information about the current alarms.
- `cloudwatch:GetMetricData`: This permission is required to retrieve metric data for the specified metrics.

_EC2 Permissions_

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-show-impairedvol.py [arguments]`

### Arguments

- `--volumeid VOL_ID`: If this argument is supplied, the script will create a CloudWatch Alarm for the specified volume ID only. Otherwise, it creates alarms for all volumes.
- `--verbose`: If this argument is supplied, the script will output additional information.
- `--impaired-alarm-for-all-volumes`: If this argument is supplied, the script will create impaired volume alarms for all volumes.
- `--impaired-alarm-cleanup`: If this argument is supplied, the script will remove impaired volume alarms for non-existent volumes.
- `--all`: If this argument is supplied, the script will perform all operations.

### Examples

To run the script for a specific volume with verbose output:

`python ebs-cw-show-impairedvol.py --volumeid vol-0123456789abcdef0 --verbose`

To run the script for all volumes:

`python ebs-cw-show-impairedvol.py --all`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.

# TODO

- For the CW Dashboards, check for limits when creating/updating a dashboard.
  - Figure out what to do when the dashboard or widget limits are exceeded (new dashboard, new widget, error)
- New script that creates / updates a CW Dashboard with an Alarm Status widget.
- Add anomaly detection to the latency dashboard.
