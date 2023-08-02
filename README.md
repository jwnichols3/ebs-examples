# ebs-examples

# ebs-cw-show-latency.py

This script calculates read/write latency for an EBS volume using CloudWatch metrics.

## Usage

`python ebs-cw-show-latency.py`

## Argument

`no arguments` - this will gather all EBS volume metrics for the last 5 minutes and display read/write latency in table format for volumes attached to running EC2 instances.
`--show-all` - this will gather all EBS volume metrics for the last 5 minutes regardless of attached EC2 instance status.
`--repeat #` - this will run the script # number of times.
`--volume-id VOLUME_ID` - specify a specific EBS volume ID to calculate latency for.

### Requirements

This scipt assumes

- You are connected to an AWS account as your default profile.
- The following Python modules are installed: boto3, argparse, datetime, tabulate

## What it Does

Retrieves the following CloudWatch metrics for the given volume over the last 5 minutes:

- VolumeTotalReadTime
- VolumeTotalWriteTime
- VolumeReadOps
- VolumeWriteOps

Calculates the average read latency as:
`(VolumeTotalReadTime / VolumeReadOps) * 1000`
Calculates the average write latency as:
`(VolumeTotalWriteTime / VolumeWriteOps) * 1000`

Prints out the read, write, and total latency in milliseconds. Also included in the print out are relevant metrics used to calculate latency.

The default time period is 300 seconds (5 minutes) but can be configured by changing the TIME_PERIOD constant.
