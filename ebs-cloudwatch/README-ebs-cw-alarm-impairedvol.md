# ebs-cw-alarm-impairedvol.py

## Overview

This Python script is designed to manage AWS CloudWatch Impaired Volume Alarms for EBS (Elastic Block Store) volumes.

The script provides functionalities to create, update, and clean up CloudWatch Alarms for EBS volumes in an impaired state.

It checks the Impaired Volume alarm configurations, ensures that the alarm descriptions are up-to-date, and removes any outdated alarms.

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

- `--volume-id`: Specify a specific EBS volume ID to operate on.
- `--create`: Create CloudWatch Alarms for the specified EBS volumes.
- `--cleanup`: Remove CloudWatch Alarms that are no longer needed.
- `--update`: Update existing CloudWatch Alarms for the specified EBS volumes.
- `--region`: AWS region where the EBS volumes are located (defaults to `us-west-2`).
- `--all`: Perform all operations: cleanup, create, and update.
- `--verbose`: Enable verbose logging.
- `--debug`: Enable debug logging.

## Details about the Main Options

### CONSTANTS

These are the constants used in the script.

- _INCLUDE_OK_ACTION_: A boolean flag that, when set to True, will include the "OK" state change of the CloudWatch Alarm in the SNS notifications. If set to False, only the "ALARM" state changes will trigger SNS notifications.

- _SNS_OK_ACTION_ARN_: The Amazon Resource Name (ARN) for the SNS topic to which "OK" state changes should be published. This is used only if INCLUDE_OK_ACTION is set to True.

- _SNS_ALARM_ACTION_ARN_: The ARN for the SNS topic to which "ALARM" state changes should be published.

- _PAGINATION_COUNT_: The maximum number of results to return in each paginated AWS API call for describing volumes or CloudWatch alarms.

- _ALARM_EVALUATION_TIME_: The period, in seconds, over which the CloudWatch metric data points are evaluated against the alarm conditions.

- _METRIC_PERIOD_: The granularity, in seconds, of the returned CloudWatch metric data points. In this script, it is set to be the same as ALARM_EVALUATION_TIME.

### `--create` Option

When the script is run with the `--create` option, it performs the following actions:

1. **Initialize AWS Clients**: Initializes AWS EC2, CloudWatch, and SNS clients for the specified region.

2. **Fetch Existing Volumes and Alarms**:

   - Fetches all existing EBS volume IDs in the AWS account within the specified region.
   - Fetches all existing CloudWatch Alarms related to EBS volumes.

3. **Check SNS Existence**: Validates the existence of the SNS topic specified by the ARN in the script. If the SNS topic does not exist or if there are permission issues, the script will exit with an error.

4. **Alarm Creation**:

   - Iterates through each EBS volume.
   - For each volume, checks if an alarm with the naming convention `ImpairedVol_<Volume_ID>` already exists.
   - If no such alarm exists, it creates a new CloudWatch Alarm for the volume with the following metrics and conditions:
     - (`VolumeQueueLength` + `VolumeReadOps`) = 0 and
     - `VolumeWriteBytes` > 0
     - For more than `5` minutes
   - The alarm also gets an action to notify a specified SNS topic when triggered.

5. **Logging**: Information and errors are logged based on the logging level set (default, verbose, or debug).

6. **Summary**: At the end, a summary is printed to the console indicating the number of new alarms created.

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

### `--update` Option

This option exists to update the CW Alarm Description in the event the EBS Volume context has changed. The EBS Volume Context is defined by you. In this example script, it is a set of text plus tags. There is an example in this script of looking at a single tag. If that tag does not exist, it add all of the EBS Volume tags to the Alarm Description.

When the script is invoked with the `--update` flag, it performs the following tasks:

1. **Initialize AWS Clients**: Initializes AWS EC2, CloudWatch, and SNS clients for the given region.

2. **Fetch Existing Volumes and Alarms**:

   - Gathers all EBS volume IDs existing in the AWS account within the specified region.
   - Retrieves the names of all existing CloudWatch Alarms pertaining to EBS volumes.

3. **Update Alarms**:

   - Iterates through each EBS volume ID.
   - Checks if a corresponding CloudWatch Alarm exists for the volume.
   - If an alarm exists, the script checks to see if the alarm description has changed. If so, it updates the alarm description with the latest volume details, such as tags and the attached EC2 instance. The `generate_alarm_description` function defines the contents of the alarm description.
   - If an alarm doesn't exist for the volume, the volume ID is noted for further reference.

4. **Logging**:

   - Informational and error messages are logged based on the chosen logging level (default, verbose, or debug).

5. **Summary**:

   - At the end, a summary is displayed, indicating the number of alarms that were updated.
   - Any volumes without a corresponding CloudWatch Alarm are listed.

The `--update` option is useful for keeping the CloudWatch Alarms' descriptions in sync with the latest state of the EBS volumes, thereby ensuring that the alarms are up-to-date and accurately reflect the volumes they are monitoring.

## Usage Examples

### To manage alarms for all volumes in the default region (us-west-2):

```bash
python script_name.py --all
```

### To create alarms for a specific volume in a specific region:

```bash
python script_name.py --create --volume-id vol-0123456789abcdef --region us-east-1
```

### To clean up alarms in the default region:

```bash
python script_name.py --cleanup
```

### To update existing alarms with verbose logging:

```bash
python script_name.py --update --verbose
```

Replace `script_name.py` with the actual name of the script.
