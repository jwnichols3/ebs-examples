# ebs-cw-alarm-manager.py

## Overview

This Python script is designed to manage AWS CloudWatch Alarms for EBS (Elastic Block Store) volumes.

The script provides functionalities to create, update, and clean up CloudWatch Alarms for EBS volumes for the following areas:

- Impaired Volume
- Read Latency
- Write Latency

## Features

- Create CloudWatch Alarms for EBS volumes.
- Cleanup CloudWatch Alarms that are no longer needed.
- Support for multiple alarm types: `ImpairedVolume`, `ReadLatency`, and `WriteLatency`.
- Filter EBS volumes by tags.
- Verbose and Debug mode for logging.

## Prerequisites

- AWS CLI configured with appropriate permissions.
- Python 3.x installed.
- `boto3` library installed. You can install it using pip: `pip install boto3`.
- AWS account with EBS volumes and CloudWatch enabled.

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

## Options

- `--create`: Create CloudWatch Alarms for the specified EBS volumes.
- `--cleanup`: Remove CloudWatch Alarms that are no longer needed.
- `--tag`: the Tag Name and Tag Value to filter EBS volumes by (example: `--tag ClusterName HDFS_PROD_1` will search and apply to just the EBS volumes that have a tag `ClusterName` with a value of `HDFS_PROD_1`)
- `--region`: AWS region where the EBS volumes are located (defaults to `us-west-2`).
- `--verbose`: Enable verbose logging.
- `--debug`: Enable debug logging.

## Details about the Main Options

### CONSTANTS

These are the constants used in the script.

**Global Settings**

- _PAGINATION_COUNT_: EBS Get volume pagination count
- _DEFAULT_REGION_: AWS Region to query and create CloudWatch Alarms in.
- _INCLUDE_OK_ACTION_: If set to False, this will not send the "OK" state change of the alarm to SNS
- _SNS_OK_ACTION_ARN_: Consider this the default if --sns-topic is not passed
- _SNS_ALARM_ACTION_ARN_: For simplicity, use same SNS topic for Alarm and OK actions

**ImpairedVol Setting**

- _ALARM_IMPAIREDVOL_NAME_PREFIX_: A clean way to identify these automatically created Alarms.
- _ALARM_IMPAIREDVOL_EVALUATION_TIME_: Frequency of Alarm Evaluation.
- _ALARM_IMPAIREDVOL_METRIC_PERIOD_: Has to be the same as Evaluation Time (for now).
- _ALARM_IMPAIREDVOL_EVALUATION_PERIODS_: How many times does the threshold have to breached before setting off the alarm
- _ALARM_IMPAIREDVOL_DATAPOINTS_TO_ALARM_: Minimum number of datapoints the alarm needs within the alarm period
- _ALARM_IMPAIREDVOL_THRESHOLD_VALUE_: Threshold value for alarm

**ReadLatency Settings**

- _ALARM_READLATENCY_NAME_PREFIX_: A clean way to identify these automatically created Alarms.
- _ALARM_READLATENCY_THRESHOLD_VALUE_: Threshold value for alarm
- _ALARM_READLATENCY_EVALUATION_TIME_: Frequency of Alarm Evaluation.
- _ALARM_READLATENCY_METRIC_PERIOD_: has Evaluation Time Has to tbe the same (for now).
- _ALARM_READLATENCY_EVALUATION_PERIODS_: How many times does the threshold have to breached before setting off the alarm
- _ALARM_READLATENCY_DATAPOINTS_TO_ALARM_: Minimum number of datapoints the alarm needs within the alarm period

**WriteLatency Settings**

- _ALARM_WRITELATENCY_NAME_PREFIX_: A clean way to identify these automatically created Alarms.
- _ALARM_WRITELATENCY_THRESHOLD_VALUE_: Threshold value for alarm
- _ALARM_WRITELATENCY_EVALUATION_TIME_: Frequency of Alarm Evaluation.
- _ALARM_WRITELATENCY_METRIC_PERIOD_: has to be the same as Evaulation Time (for now).
- _ALARM_WRITELATENCY_EVALUATION_PERIODS_: How many times does the threshold have to breached before setting off the alarm
- _ALARM_WRITELATENCY_DATAPOINTS_TO_ALARM_: Minimum number of datapoints the alarm needs within the alarm period

### `--create` Option

When the script is run with the `--create` option, it performs the following actions:

1. **Initialize AWS Clients**: Initializes AWS EC2, CloudWatch, and SNS clients for the specified region.

2. **Validates the SNS topic:** Checks to make sure the SNS topic is available and accessible.

3. **Fetch Existing Volumes and Alarms**:

   - Fetches all existing EBS volume IDs in the AWS account within the specified region.
   - Fetches all existing CloudWatch Alarms related to EBS volumes.

4. **Check SNS Existence**: Validates the existence of the SNS topic specified by the ARN in the script. If the SNS topic does not exist or if there are permission issues, the script will exit with an error.

5. **Alarm Creation**:

   - Iterates through each EBS volume.
   - For each volume, checks if an alarm with the naming convention `ImpairedVol_<Volume_ID>` already exists.
   - If no such alarm exists, it creates a new CloudWatch Alarm for the volume with the following metrics and conditions:
     - (`VolumeQueueLength` + `VolumeReadOps`) = 0 and
     - `VolumeQueueLenght` > 0
     - For more than `5` minutes
   - The alarm also gets an action to notify a specified SNS topic when triggered.

6. **Logging**: Information and errors are logged based on the logging level set (default, verbose, or debug).

7. **Summary**: At the end, a summary is printed to the console indicating the number of new alarms created.

This option allows users to automate the creation of CloudWatch Alarms for all EBS volumes that do not already have an alarm set up. It's especially useful for environments where new volumes are frequently created.

### `--cleanup` Option

When the script is run with the `--cleanup` option, it performs the following series of actions:

1. **Initialize AWS Clients**: The script initializes AWS EC2, CloudWatch, and SNS clients for the specified region.

2. **Fetch Existing Volumes and Alarms**:

   - Retrieves all existing EBS volume IDs in the AWS account within the specified region.
   - Fetches the names of all existing CloudWatch Alarms related to EBS volumes.

3. **Alarm Cleanup**:

   - Iterates through each CloudWatch Alarm whose name starts with `ImpairedVol_`.
   - Extracts the EBS volume ID from the alarm name.
   - Checks if the corresponding EBS volume still exists.
   - If the EBS volume does not exist, the script deletes the CloudWatch Alarm.
   - If the EBS volume does exist, the alarm is left unchanged.

4. **Logging**:

   - Information and errors are logged based on the logging level set (default, verbose, or debug).

5. **Summary**:
   - At the end, a summary is printed to the console indicating the number of alarms deleted.

This option is useful for cleaning up old or redundant CloudWatch Alarms related to EBS volumes that no longer exist, helping to maintain a cleaner and more manageable monitoring setup.

## Usage Examples

### Create All

```
python ebs-cw-alarm-manager.py --create --alarm-type all
```

### Create just ImpairedVol

```
python ebs-cw-alarm-manager.py --create --alarm-type impairedvol
```

### Clean up all

```bash
python ebs-cw-alarm-manager.py --cleanup --alarm-type all

```
