# ebs-examples

# Overview

This repository contains Python scripts that demonstrate the use of AWS SDK (boto3) to interact with Amazon EBS volumes and AWS CloudWatch. These scripts provide a variety of functionality, including creating CloudWatch Alarms for "stuck" volumes, calculating and displaying the read, write, and overall latency for EBS volumes, and creating a CloudWatch Dashboard for EBS latency metrics.

# Disclaimer

Please note: These scripts are intended for educational purposes and are not recommended for production use. Always test scripts in a controlled environment before using them in a production capacity.

# Python Scripts

These are the Python scripts included in this repository. More details of each script are provided below.

`ebs-cw-alarm-stuckvol.py`

This Python script creates AWS CloudWatch Alarms for Amazon EBS volumes. These alarms are designed to alert when an EBS volume becomes "stuck." A "stuck" volume is one that has a queue length but no read or write operations.

`ebs-cw-dashboard-latency.py`

This Python script creates a CloudWatch Dashboard named "Read and Write Latency". The dashboard includes two calculated metrics for every EBS volume in the AWS Account.

`ebs-cw-show-latency.py`

This Python script calculates and displays the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

`ebs-cw-show-stuckvol.py`

This Python script monitors the I/O operations for Amazon EBS volumes in an AWS account and creates CloudWatch Alarms for "stuck" volumes. A "stuck" volume is one that has a queue length but no read or write operations.

## ebs-cw-alarm-stuckvol.py

EBS Stuck Volume CloudWatch Alarm Script

This Python script uses the AWS SDK (boto3) to create AWS CloudWatch Alarms for Amazon EBS volumes. The purpose of these alarms is to alert when EBS volumes become "stuck," or unresponsive. The script provides options to create alarms for a specific volume, for all volumes, or to clean up alarms for volumes that no longer exist.

Change the `SNS_ALARM_ACTION_ARN` variable to an SNS topic ARN to send alarm notifications.

### Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)

### Installation

Ensure that you have Python 3.6+ installed, along with Boto3. You can install Boto3 with pip:

`pip install boto3`

Then, download the Python script `ebs-cw-alarm-stuckvol.py`.

### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-alarm-stuckvol.py [arguments]`

### Arguments

- `--volumeid`: Specify the ID of a new EBS volume to create an alarm for.
- `--verbose`: Enable verbose output.
- `--stuck-alarm-for-all-volumes`: Create stuck volume alarms for all EBS volumes.
- `--stuck-alarm-cleanup`: Remove stuck volume alarms for non-existent volumes.
- `--all`: Perform all operations: add stuck volume alarms for all volumes and remove alarms for non-existent volumes.

If the script is run without any arguments, it will display help output.

### Examples

To create a stuck volume alarm for a specific EBS volume:

`python ebs-cw-alarm-stuckvol.py --volumeid vol-0abcdefgh123`

To create stuck volume alarms for all EBS volumes and to remove alarms for volumes that no longer exist:

`python ebs-cw-alarm-stuckvol.py --all`

## ebs-cw-dashboard-latency.py

EBS CloudWatch Dashboard Latency Script

This Python script uses the AWS SDK (boto3) to create a CloudWatch Dashboard named "Read and Write Latency". The dashboard includes two calculated metrics for every EBS volume in the AWS Account: EBS Write Latency and EBS Read Latency. The script ensures that the metrics are only created if they don't already exist.

### Requirements:

- Python 3.6+
- Boto3 (AWS SDK for Python)
- AWS credentials configured (can be configured using the AWS CLI)

### Installation:

1. Make sure that you have Python 3.6 or newer installed.
2. Install Boto3 using pip (`pip install boto3`).
3. Download the Python script "ebs-cw-dashboard-latency.py".

### Usage:

You can run the script from the command line with the following syntax:
`python ebs-cw-dashboard-latency.py [arguments]`

### Arguments:

- `--verbose`: If this argument is supplied, the script will output debug statements.
- `--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

### Examples:

To run the script with verbose output:
`python ebs-cw-dashboard-latency.py --verbose`

To see what the dashboard JSON would look like without actually creating the dashboard:
`python ebs-cw-dashboard-latency.py --dry-run`

## ebs-cw-show-latency.py

EBS CloudWatch Show Latency Script

This Python script uses the AWS SDK (boto3) to calculate and display the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

### Requirements:

- Python 3.6+
- Boto3 (AWS SDK for Python)
- AWS credentials configured (can be configured using the AWS CLI)

### Installation:

- Ensure that you have Python 3.6 or newer installed.
- Install Boto3 using pip (pip install boto3).
- Download the Python script "ebs-cw-show-latency.py".

### Usage:

You can run the script from the command line with the following syntax:
python ebs-cw-show-latency.py [arguments]

### Arguments:

`--volume-id VOL_ID`: If this argument is supplied, the script will calculate the latency for the specified volume ID only. Otherwise, it calculates latency for all volumes.
`--verbose`: If this argument is supplied, the script will output additional information.
`--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

### Examples:

To run the script for a specific volume with verbose output:
`python ebs-cw-show-latency.py --volume-id vol-0123456789abcdef0 --verbose`

To run the script for all volumes:
`python ebs-cw-show-latency.py`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.

## ebs-cw-show-stuckvol.py

EBS CloudWatch Show Stuck Volumes Script
This script is a Python program that uses the AWS SDK (boto3) to monitor the I/O operations for Amazon EBS volumes in an AWS account and create CloudWatch Alarms for "stuck" volumes. A "stuck" volume is one that has a queue length but no read or write operations.

### Requirements:

- Python 3.6+
- Boto3 (AWS SDK for Python)
- AWS credentials configured (can be configured using the AWS CLI)
- Installation:
- Ensure that you have Python 3.6 or newer installed.
- Install Boto3 using pip (pip install boto3).
- Download the Python script "ebs-cw-show-stuckvol.py".

### Usage:

You can run the script from the command line with the following syntax:
python ebs-cw-show-stuckvol.py [arguments]

### Arguments:

`--volumeid VOL_ID`: If this argument is supplied, the script will create a CloudWatch Alarm for the specified volume ID only. Otherwise, it creates alarms for all volumes.
`--verbose`: If this argument is supplied, the script will output additional information.
`--stuck-alarm-for-all-volumes`: If this argument is supplied, the script will create stuck volume alarms for all volumes.
`--stuck-alarm-cleanup`: If this argument is supplied, the script will remove stuck volume alarms for non-existent volumes.
`--all`: If this argument is supplied, the script will perform all operations.

### Examples:

To run the script for a specific volume with verbose output:
`python ebs-cw-show-stuckvol.py --volumeid vol-0123456789abcdef0 --verbose`

To run the script for all volumes:
`python ebs-cw-show-stuckvol.py --all`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.
