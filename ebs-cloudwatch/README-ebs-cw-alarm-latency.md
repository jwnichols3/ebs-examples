# Converged into the [ebs-cw-alarm-manager.py](./ebs-cw-alarm-manager.py) script

# EBS Latency CloudWatch Alarm

This script creates and manages CloudWatch alarms for EBS volume read latency.

## Usage

python ebs-cw-alarm-latency.py [options]

## Functionality

- Gets all EBS volumes in the account
- Checks for existing read latency alarms
- Creates a new alarm or updates existing alarm per volume
- Alarms trigger when read latency exceeds threshold for specified periods
- Alarm actions send SNS notifications
- This automates read latency monitoring and alarms for EBS volumes.

## Options

`--tag` <tag> - Only create/update alarms for volumes with this tag
`--refresh` - Refresh all alarms even if they already exist
`--tagless` - Create alarms for volumes without a Name tag
`--rename` - Rename existing alarms instead of updating in place
`--threshold <ms>` - Alarm threshold in milliseconds, default 200
`--periods <num>` - Consecutive periods to trigger alarm, default 1
`--sns-topic <ARN>` - SNS topic for alarm actions, default in script
