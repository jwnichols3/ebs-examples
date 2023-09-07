import boto3
import argparse
import sys

# Change this to your SNS topic ARN.
SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"
PAGINATION_COUNT = 100  # number of items per Boto3 page call


def check_sns_exists():
    try:
        response = sns.get_topic_attributes(TopicArn=SNS_ALARM_ACTION_ARN)
        return True
    except Exception as e:
        print(f"Error checking SNS: {e}")
        sys.exit(1)


def create_read_latency_alarm(volume_id, tagname, cloudwatch):
    if not check_sns_exists():
        print("Alarm creation failed due to invalid SNS ARN.")
        return

    alarm_name = (
        "Read Latency " + tagname + " " + volume_id
        if tagname
        else "Read Latency " + volume_id
    )

    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": [SNS_ALARM_ACTION_ARN],
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 200,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "(m1 / m2) * 1000",
                "Label": "ReadLatency",
                "ReturnData": True,
            },
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeTotalReadTime",
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
                        "MetricName": "VolumeReadOps",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }

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


# Parse arguments
parser = argparse.ArgumentParser(
    description="Create CloudWatch Alarms for EBS Read Latency."
)
parser.add_argument("--tag", help="Tag name to be appended to Alarm name")
args = parser.parse_args()

# Create EC2 and CloudWatch clients
ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")
sns = boto3.client("sns")

# Get all volumes
paginator_vols = ec2.get_paginator("describe_volumes")
volume_ids = []

for page in paginator_vols.paginate(MaxResults=PAGINATION_COUNT):
    for volume in page["Volumes"]:
        volume_ids.append(volume["VolumeId"])

# Get all alarms
paginator_alarms = cloudwatch.get_paginator("describe_alarms")
alarm_names = []

for page in paginator_alarms.paginate(MaxRecords=PAGINATION_COUNT):
    for alarm in page["MetricAlarms"]:
        alarm_names.append(alarm["AlarmName"])

# Create alarm for each volume
for volume_id in volume_ids:
    tagname = ""
    if args.tag:
        volume = ec2.describe_volumes(VolumeIds=[volume_id])
        tags = volume["Volumes"][0].get("Tags", [])
        for tag in tags:
            if tag["Key"] == args.tag:
                tagname = tag["Value"]
                break

    if tagname or not args.tag:
        alarm_name = (
            "EBS Read Latency " + tagname
            if tagname
            else "EBS Read Latency " + volume_id
        )
        if alarm_name not in alarm_names:
            create_read_latency_alarm(volume_id, tagname, cloudwatch)
        else:
            print(f"Alarm '{alarm_name}' already exists for volume {volume_id}")

# If no arguments were provided, display the help message
if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)
