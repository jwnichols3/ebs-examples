# EBS CloudWatch Examples

## TODO

[CloudWatch Examples To Do List](TODO.md)

## Overview

This folder contains the stand-alone Python scripts to update CloudWatch Alarms, show if any EBS volumes are in the Impaired status, show latency metrics, create custom CloudWatch metrics for read and write latency, example CloudWatch dashboards, and more.

There is a [Cross-Account, Cross-Region folder](./ebs-cloudwatch-cross-account/) that includes examples of how to retrieve metrics from other AWS accounts and regions and publish to a central CloudWatch Dashboard using the CLoudWatch Observability Access Manager (OAM) feature.

## Disclaimer

Please note: These scripts are intended for educational purposes and are not recommended for production use. Always test scripts in a controlled environment before using them in a production capacity. There is minimum error handling implemented and not all scenarious are accounted for such as scale, access controls, and input validation. There is an inherent assumption that you have a way to run these scripts on a system that has access to the AWS account in question and the required privileges.

## Python Scripts Overview

These are the Python scripts included in this repository. More details of each script are provided below. These are configured as stand-alone scripts so there are repeated sections for things like importing libraries and establishing AWS credentials that could be refactored into common/shared modules/functions to reduce duplication.

### ebs-cloudwatch directory

[`ebs-cw-alarm-manager.py`](./ebs-cw-alarm-manager.py)

This script replaces the `impairedvol` and `latency` scripts for CloudWatch Alarms. This script has options to deploy Impaired Volume, Read Latency, and Write Latency alarms.

The Impaired Volume alarms are designed to alert when an EBS volume becomes "impaired." A "impaired" volume is one that has a queue length but no read or write operations.

[`ebs-cw-dashboard-volumestatus.py`](./ebs-cw-dashboard-volumestatus.py)

This script creates CloudWatch dashboards for EBS volumes, filtered optionally by tag.

This script calls AWS APIs to get a list of EBS volumes, extracts volume IDs
and CloudWatch metrics for each volume, and creates CloudWatch dashboards
displaying those metrics.

Dashboards are sharded to stay within CloudWatch dashboard size limits. Stale
dashboards are cleaned up based on the set dashboard name prefix.

[`ebs-cw-show-detailed-metrics-for-latency-by-vol.py`](./ebs-cw-show-detailed-metrics-for-latency-by-vol.py)

This Python script prints detailed CloudWatch metrics for read, write, and overall latency for each EBS volume in the AWS account. It calculates and prints these metrics for each volume for a given time frame (defaulting in the last 24 hours). This provides visibility into the latency performance of each EBS volume over time. You can use this with the `--style` option of `tvs` to output in a tabular format for easy importing into spreadsheets or other tools.

[`ebs-cw-show-latency-metrics-current.py`](./ebs-cw-show-latency-metrics-current.py)

This Python script calculates and displays the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

[`ebs-cw-show-impairedvol.py`](./ebs-cw-show-impairedvol.py)

This Python script monitors the I/O operations for Amazon EBS volumes in an AWS account and creates CloudWatch Alarms for "impaired" volumes. A "impaired" volume is one that has a queue length but no read or write operations.

[`ebs-cw-custom-metric-latency-batch.py`](./ebs-cw-custom-metric-latency-batch.py)

This Python script collects CloudWatch metrics required to calculate Read and Write Latency per EBS Volume. It then batch writes custom Read, Write, and Total Latency metrics per volume into CloudWatch. Having the custom metrics for Latency enables the creation of dashboards that leverage dynamic queries (as of Sep 2023, CloudWatch dashboards support a single metric query - latency requires a complex query).

[`ebs-cw-custom-metric-latency.py`](./ebs-cw-custom-metric-latency.py)

This Python script collects CloudWatch metrics required to calculate Read and Write Latency per EBS Volume. It then puts custom Read, Write, and Total Latency metrics per volume into CloudWatch. Having the custom metrics for Latency enables the creation of dashboards that leverage dynamic queries (as of Sep 2023, CloudWatch dashboards support a single metric query - latency requires a complex query). There is an example dashboard configuration included that shows the Top 10 Read Latency by volume.

Note: the difference between the `-batch` and non batch version are included to show you the difference between cycling through each volume individually vs batch processing all volumes at once. Batch processing is more efficient for large fleets but the non-batch version may be easier to follow from a code perspective.

### CloudWatch Dashboard Examples in ebs-cloudwatch directory

This folder also contains example CloudWatch dashboard JSON files that visualize EBS metrics including latency. These dashboards leverage the custom latency metrics created by the Python scripts.

There are two example dashboards included:

- [`ebs-cw-dashboard-top10-read-latency.json`](./ebs-cw-dashboard-top10-read-latency.json) - Shows the top 10 volumes by read latency using the custom read latency metric. More information in the [Dashboard README](./README-cw-dashboard-top10.md).
- [`ebs-cw-dashboard-read-write-latency.json`](./ebs-cw-latency-dashboard-example.json)

These are examples of dashboards that visualize read latency, write latency, and total latency for EBS volumes using the custom latency metrics created by the Python scripts. The top 10 read latency dashboard shows the volumes with the highest read latency, while the read/write dashboard shows these metrics for all volumes on a single dashboard.

## Python Script Details

There are three categories of scripts:

- CloudWatch Alarms
- CloudWatch Dashboards
- CloudWatch Custom Metrics
- CLI-based scripts that print CloudWatch data.

### CloudWatch Alarm Scripts

#### ebs-cw-alarm-manager.py

Details are in [README-ebs-cw-alarm-manager](./README-ebs-cw-alarm-manager.md)

### CloudWatch Custom Metrics

#### ebs-cw-custom-metric-latency-batch.py and ebs-cw-custom-metric-latency.py

Note: the difference between the `-batch` and non batch version are included to show you the difference between cycling through each volume individually vs batch processing all volumes at once. Batch processing is more efficient for large fleets but the non-batch version may be easier to follow from a code perspective.

This Python script collects CloudWatch metrics required to calculate Read and Write Latency per EBS Volume. It then puts custom Read, Write, and Total Latency metrics per volume into CloudWatch. Having the custom metrics for Latency enables the creation of dashboards that leverage dynamic queries (as of Sep 2023, CloudWatch dashboards support a single metric query - latency requires a complex query).

##### Method

Retrieves the following metrics from CloudWatch for all EBS volumes:

- VolumeTotalReadTime
- VolumeTotalWriteTime
- VolumeReadOps
- VolumeWriteOps

Calculates read and write latency per volume based on total time and ops

Publishes custom CloudWatch metrics for each volume:

- VolumeReadLatency
- VolumeWriteLatency
- VolumeTotalLatency

Metrics are put in batches for efficiency

##### Usage

`python ebs-cw-custom-metric-latency-batch.py [options]`

##### Options

--repeat: Number of times to repeat metric collection. Default is 1.
--sleep: Seconds to sleep between repeats. Default is 5.
--verbose: Enable debug logging.

##### Requirements

boto3

##### Credentials configured to access CloudWatch

EC2 Permissions:
`ec2:DescribeVolumes`

This permission is required to get details about EBS volumes.

CloudWatch Permissions:

`cloudwatch:GetMetricData`

This permission is required to get CloudWatch metrics for the EBS volumes.

`cloudwatch:PutMetricData`

This permission is required to publish custom metrics to CloudWatch.

Here is an example IAM Policy with these permissions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:DescribeVolumes"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:GetMetricData", "cloudwatch:PutMetricData"],
      "Resource": "*"
    }
  ]
}
```

### CloudWatch Dashboards

These are example Python scripts that create CloudWatch dashboards for different scenarios. As these evolve, the individual scripts will converge into a single script that takes parameters to control what type of dashboard to create.

#### ebs-cw-dashboard-volumestatus.py

This script creates CloudWatch dashboards for EBS volumes, filtered optionally by tag, and with the ability to query EBS volumes in different regions than the CloudWatch dashboards are created.

It calls AWS APIs to:

- Get a list of EBS volumes
- Extract volume IDs
- Get CloudWatch metrics for each volume
- Create CloudWatch dashboards displaying those metrics

Dashboards are sharded to stay within CloudWatch limits. Stale dashboards are cleaned up based on the dashboard name prefix.

##### Features

- Retrieves list of EBS volumes using EC2 API
- Gets CloudWatch metrics for each volume
- Creates sharded CloudWatch dashboards for volumes
- Dashboards display volume metrics
- Can filter volumes by tag
- Cleans up stale dashboards by name prefix

##### Usage

```bash
python ebs-cw-dashboard-volumestatus.py [options]
```

##### Options

- `--ebs-region` - AWS region for EBS volumes
- `--cw-region` - AWS region for the CloudWatch Dashboards
- `--tag` - Only include volumes with this tag
- `--verbose`

##### Configuration

- `EBS_REGION` - Default EBS region
- `DASHBOARD_NAME_PREFIX` - Dashboard name prefix
- `DASHBOARD_PERIOD` - Dashboard default period
- `DASHBOARD_WIDGET_WIDTH` - Widget width
- `DASHBOARD_WIDGET_HEIGHT` - Widget height

#### ebs-cw-dashboard-latency.py

Create EBS CloudWatch Dashboard with Volume Latency.

This Python script uses the AWS SDK (boto3) to create a CloudWatch Dashboard named "Read and Write Latency". The dashboard includes two calculated metrics for every EBS volume in the AWS Account: EBS Write Latency and EBS Read Latency. The script ensures that the metrics are only created if they don't already exist.

Note: There are limits to the CloudWatch Dashboard and Graphs. As of the time of this script, the overall Dashboard has a limit of 2500 time series and each graph has a limit of 500 time series. Check the [CloudWatch Service Limits](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html) to verify.

##### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Argparse
- AWS credentials configured (can be configured using the AWS CLI)

##### Python Module Installation

1. Make sure that you have Python 3.6 or newer installed.
2. Install Boto3 using pip (`pip install boto3 argparse`).

##### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:PutDashboard`: This permission is required to create or modify dashboards in CloudWatch.
- `cloudwatch:DeleteDashboards`: This permission is required to delete dashboards.
- `cloudwatch:ListMetrics`: This permission is required to retrieve a list of the current metrics.
- `cloudwatch:GetDashboard`: This permission is required to retrieve information about specific dashboards.
- `cloudwatch:DescribeAlarmHistory`: This permission is required to retrieve the history of a specific alarm.

EC2 Permissions

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

##### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-dashboard-latency.py [arguments]`

##### Arguments

- `--verbose`: If this argument is supplied, the script will output debug statements.
- `--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

##### Examples

To run the script with verbose output:

`python ebs-cw-dashboard-latency.py --verbose`

To see what the dashboard JSON would look like without actually creating the dashboard:

`python ebs-cw-dashboard-latency.py --dry-run`

#### ebs-cw-show-latency-metrics-current.py

Show the EBS CloudWatch Latency Metrics in table format.

This Python script uses the AWS SDK (boto3) to calculate and display the read, write, and overall latency for EBS volumes in an AWS account. It uses CloudWatch metrics to calculate the latencies.

Read Latency is calculated `(TotalReadTime / TotalReadOps) * 1000`

Write Latency is calculated `(TotalWriteTime / TotalWriteOps) * 1000`

(note: the `* 1000` is about readability - 4.01 vs .0041)

##### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Tabulate and Argparse
- AWS credentials configured (can be configured using the AWS CLI)

##### Python Module Installation

- Ensure that you have Python 3.6 or newer installed.
- Install Boto3, tabulate, and argparse using pip (pip install boto3 tabulate argparse).

##### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:GetMetricStatistics`: This permission is required to retrieve statistical data for a specified metric.
- `cloudwatch:ListMetrics`: This permission is required to retrieve a list of the current metrics.

_EC2 Permissions_

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

##### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-show-latency-metrics-current.py [arguments]`

##### Arguments

- `--volume-id VOL_ID`: If this argument is supplied, the script will calculate the latency for the specified volume ID only. Otherwise, it calculates latency for all volumes.
- `--verbose`: If this argument is supplied, the script will output additional information.
- `--dry-run`: If this argument is supplied, the script will output the JSON of the dashboard, but not create it.

##### Examples

To run the script for a specific volume with verbose output:

`python ebs-cw-show-latency-metrics-current.py --volume-id vol-0123456789abcdef0 --verbose`

To run the script for all volumes:

`python ebs-cw-show-latency-metrics-current.py`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.

### CLI Output

#### ebs-cw-show-impairedvol.py

Outout all EBS volumes, flagging any that are considered Impaired.

This script is a Python program that uses the AWS SDK (boto3) to monitor the I/O operations for Amazon EBS volumes in an AWS account and create CloudWatch Alarms for "impaired" volumes. A "impaired" volume is one that has a queue length > 0 but no read or write operations.

##### Python Requirements

- Python 3.6+
- Boto3 (AWS SDK for Python)
- Argparse
- AWS credentials configured (can be configured using the AWS CLI)

##### Python Module Installation

- Ensure that you have Python 3.6 or newer installed.
- Install Boto3 and Argepars using pip (pip install boto3 argparse).

##### AWS Access Permissions

_CloudWatch Permissions:_

- `cloudwatch:DescribeAlarms`: This permission is required to retrieve information about the current alarms.
- `cloudwatch:GetMetricData`: This permission is required to retrieve metric data for the specified metrics.

_EC2 Permissions_

- `ec2:DescribeVolumes`: This permission is required to retrieve information about the EBS volumes.

##### Usage

You can run the script from the command line with the following syntax:

`python ebs-cw-show-impairedvol.py [arguments]`

##### Arguments

- `--volumeid VOL_ID`: If this argument is supplied, the script will create a CloudWatch Alarm for the specified volume ID only. Otherwise, it creates alarms for all volumes.
- `--verbose`: If this argument is supplied, the script will output additional information.
- `--impaired-alarm-for-all-volumes`: If this argument is supplied, the script will create impaired volume alarms for all volumes.
- `--impaired-alarm-cleanup`: If this argument is supplied, the script will remove impaired volume alarms for non-existent volumes.
- `--all`: If this argument is supplied, the script will perform all operations.

##### Examples

To run the script for a specific volume with verbose output:

`python ebs-cw-show-impairedvol.py --volumeid vol-0123456789abcdef0 --verbose`

To run the script for all volumes:

`python ebs-cw-show-impairedvol.py --all`

Please note: Ensure that you replace the vol-0123456789abcdef0 in the example with the actual volume ID you want to monitor.

#### ebs-cw-show-latency-detailed-metrics-by-vol.py

#### ebs-cw-shows-latency-metrics-current.py
