import boto3
import argparse
import sys
import logging

PAGINATOR_COUNT = 100
SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def init_aws_clients():
    try:
        ec2 = boto3.client("ec2")
        cloudwatch = boto3.client("cloudwatch")
        sns = boto3.client("sns")
        return ec2, cloudwatch, sns
    except Exception as e:
        logging.error(f"Error initializing clients: {e}")
        sys.exit(1)


def check_sns_exists(sns):
    try:
        sns.get_topic_attributes(TopicArn=SNS_ALARM_ACTION_ARN)
        return True
    except Exception as e:
        logging.error(f"Error checking SNS: {e}")
        sys.exit(1)


def create_read_latency_alarm(volume_id, tagname, cloudwatch):
    try:
        alarm_name = (
            f"Read Latency {tagname} {volume_id}"
            if tagname
            else f"Read Latency {volume_id}"
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

        cloudwatch.put_metric_alarm(**alarm_details)
        print(f"New alarm '{alarm_name}' created for volume {volume_id}")
    except Exception as e:
        logging.error(f"Error creating alarm: {e}")


def main(tag=None):
    ec2, cloudwatch, sns = init_aws_clients()

    if not check_sns_exists(sns):
        logging.error("SNS topic doesn't exist or is not accessible.")
        return

    volume_ids = [
        vol["VolumeId"]
        for page in ec2.get_paginator("describe_volumes").paginate(
            MaxResults=PAGINATOR_COUNT
        )
        for vol in page["Volumes"]
    ]
    alarm_names = [
        alarm["AlarmName"]
        for page in cloudwatch.get_paginator("describe_alarms").paginate(
            MaxRecords=PAGINATOR_COUNT
        )
        for alarm in page["MetricAlarms"]
    ]

    for volume_id in volume_ids:
        tagname = ""
        if tag:
            volume = ec2.describe_volumes(VolumeIds=[volume_id])
            tags = volume["Volumes"][0].get("Tags", [])
            for t in tags:
                if t["Key"] == tag:
                    tagname = t["Value"]
                    break
        alarm_name = (
            f"Read Latency {tagname} {volume_id}"
            if tagname
            else f"Read Latency {volume_id}"
        )
        if alarm_name not in alarm_names:
            create_read_latency_alarm(volume_id, tagname, cloudwatch)
        else:
            print(f"Alarm '{alarm_name}' already exists for volume {volume_id}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Alarms for EBS Read Latency."
    )
    parser.add_argument("--tag", help="Tag name to be appended to Alarm name")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    main(tag=args.tag)
