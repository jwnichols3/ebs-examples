import boto3
import argparse


def create_alarm(volume_id, cloudwatch):
    alarm_name = volume_id + "_stuckvol"
    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": ["arn:aws:sns:us-west-2:338557412966:ebs_alarms"],
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 1.0,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "IF(m3>0 AND m1+m2==0, 1, 0)",
                "Label": "StuckVolume",
                "ReturnData": True,
            },
            {
                "Id": "m3",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeQueueLength",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeReadOps",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
            {
                "Id": "m2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeWriteBytes",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }
    # Create the new alarm
    cloudwatch.put_metric_alarm(
        AlarmName=alarm_details["AlarmName"],
        AlarmActions=alarm_details["AlarmActions"],
        EvaluationPeriods=alarm_details["EvaluationPeriods"],
        DatapointsToAlarm=alarm_details["DatapointsToAlarm"],
        Threshold=alarm_details["Threshold"],
        ComparisonOperator=alarm_details["ComparisonOperator"],
        TreatMissingData=alarm_details["TreatMissingData"],
        Metrics=alarm_details["Metrics"],
    )

    print(f"New alarm '{alarm_details['AlarmName']}' created for volume {volume_id}")


def cleanup_alarms(volume_ids, alarm_names, cloudwatch):
    for alarm_name in alarm_names:
        # Only consider alarms that end with '_stuckvol'
        if alarm_name.endswith("_stuckvol"):
            volume_id = alarm_name[: -len("_stuckvol")]
            if volume_id not in volume_ids:
                print(
                    f"Deleting alarm {alarm_name} as volume {volume_id} no longer exists"
                )
                cloudwatch.delete_alarms(AlarmNames=[alarm_name])
            else:
                print(
                    f"No change to alarm {alarm_name} as volume {volume_id} still exists"
                )


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--newvolumeid", help="The new volume ID to create the alarm for")
parser.add_argument(
    "--stuck-alarm-for-all-volumes",
    action="store_true",
    help="Add stuckvol alarms for all volumes",
)
parser.add_argument(
    "--stuck-alarm-cleanup",
    action="store_true",
    help="Remove stuckvol alarms for non-existent volumes",
)
parser.add_argument(
    "--all",
    action="store_true",
    help="Perform all operations: Add stuckvol alarms for all volumes and remove alarms for non-existent volumes",
)
args = parser.parse_args()

# Create EC2 and CloudWatch clients
ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")

# Get all volumes
volumes = ec2.describe_volumes()
volume_ids = [volume["VolumeId"] for volume in volumes["Volumes"]]

# Get all alarms
alarms = cloudwatch.describe_alarms()
alarm_names = [alarm["AlarmName"] for alarm in alarms["MetricAlarms"]]

# If --newvolumeid is provided, create alarm for this volume
if args.newvolumeid:
    if args.newvolumeid + "_stuckvol" not in alarm_names:
        create_alarm(args.newvolumeid, cloudwatch)
    else:
        print(
            f"Alarm '{args.newvolumeid}_stuckvol' already exists for volume {args.newvolumeid}"
        )

# If --stuck-alarm-for-all-volumes is provided, create alarm for all volumes
if args.stuck_alarm_for_all_volumes or args.all:
    for volume_id in volume_ids:
        if volume_id + "_stuckvol" not in alarm_names:
            create_alarm(volume_id, cloudwatch)
        else:
            print(f"Alarm '{volume_id}_stuckvol' already exists for volume {volume_id}")

# If --stuck-alarm-cleanup is provided, remove alarms for non-existent volumes
if args.stuck_alarm_cleanup or args.all:
    cleanup_alarms(volume_ids, alarm_names, cloudwatch)
