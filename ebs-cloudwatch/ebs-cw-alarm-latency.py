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


def main(tag=None, refresh=False, tagless=False):
    """
    The main function for creating or updating CloudWatch Alarms for EBS Read Latency.

    Parameters:
        tag (str): Optional tag to filter volumes.
        refresh (bool): If True, existing alarms will be updated.
        tagless (bool): If True, includes volumes without tags when updating.
    """

    ec2, cloudwatch, sns = init_aws_clients()
    skipped_tagless_volumes = []
    updated_alarms = []

    if not check_sns_exists(sns):
        logging.error("SNS topic doesn't exist or is not accessible.")
        return

    alarm_names = [
        alarm["AlarmName"]
        for page in cloudwatch.get_paginator("describe_alarms").paginate(
            MaxRecords=PAGINATOR_COUNT
        )
        for alarm in page["MetricAlarms"]
    ]

    volume_ids = [
        vol["VolumeId"]
        for page in ec2.get_paginator("describe_volumes").paginate(
            MaxResults=PAGINATOR_COUNT
        )
        for vol in page["Volumes"]
    ]

    for volume_id in volume_ids:
        tagname = ""
        volume = ec2.describe_volumes(VolumeIds=[volume_id])
        tags = volume["Volumes"][0].get("Tags", [])
        for t in tags:
            if t["Key"] == tag:
                tagname = t["Value"]
                break

        if refresh and tag and (tagname or (not tagname and tagless)):
            create_read_latency_alarm(volume_id, tagname, cloudwatch, refresh=True)
            updated_alarms.append(volume_id)
        elif tag and tagname:
            alarm_name = (
                f"Read Latency {tagname} {volume_id}"  # construct the alarm name
            )
            if alarm_name not in alarm_names:  # Check if the alarm already exists
                create_read_latency_alarm(volume_id, tagname, cloudwatch)
            else:
                logging.info(
                    f"Skipping existing alarm '{alarm_name}' for volume {volume_id}"
                )
        elif not tag:
            alarm_name = f"Read Latency {volume_id}"  # construct the alarm name
            if refresh:  # If refresh flag is set, update the alarm
                create_read_latency_alarm(volume_id, tagname, cloudwatch, refresh=True)
            elif alarm_name not in alarm_names:  # Check if the alarm already exists
                create_read_latency_alarm(volume_id, tagname, cloudwatch)
            else:
                logging.info(
                    f"Skipping existing alarm '{alarm_name}' for volume {volume_id}"
                )

    if skipped_tagless_volumes:
        logging.info(
            f"Skipped volumes without tag: {', '.join(skipped_tagless_volumes)}"
        )

    if updated_alarms:
        logging.info(f"Updated alarms for volumes: {', '.join(updated_alarms)}")


def init_aws_clients():
    """
    Initialize AWS service clients.

    Returns:
        ec2, cloudwatch, sns: boto3 client objects for EC2, CloudWatch, and SNS.
    """
    try:
        ec2 = boto3.client("ec2")
        cloudwatch = boto3.client("cloudwatch")
        sns = boto3.client("sns")
        return ec2, cloudwatch, sns
    except Exception as e:
        logging.error(f"Error initializing clients: {e}")
        sys.exit(1)


def check_sns_exists(sns):
    """
    Check if the SNS topic exists.

    Parameters:
        sns (boto3.SNS.Client): The boto3 SNS client object.

    Returns:
        bool: True if the SNS topic exists, False otherwise.
    """
    try:
        sns.get_topic_attributes(TopicArn=SNS_ALARM_ACTION_ARN)
        return True
    except Exception as e:
        logging.error(f"Error checking SNS: {e}")
        sys.exit(1)


def create_read_latency_alarm(volume_id, tagname, cloudwatch, refresh=False):
    """
    Create or update a CloudWatch Alarm for EBS Read Latency.

    Parameters:
        volume_id (str): The EBS volume ID.
        tagname (str): The tag name for the alarm.
        cloudwatch (boto3.CloudWatch.Client): The boto3 CloudWatch client object.
        refresh (bool): If True, the existing alarm will be updated.
    """
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

        if refresh:
            cloudwatch.delete_alarms(AlarmNames=[alarm_name])

        cloudwatch.put_metric_alarm(**alarm_details)
        logging.info(
            f"New or updated alarm '{alarm_name}' created for volume {volume_id}"
        )
    except Exception as e:
        logging.error(f"Error creating or updating alarm: {e}")


def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Alarms for EBS Read Latency."
    )
    parser.add_argument("--tag", help="Tag name to be appended to Alarm name")
    parser.add_argument(
        "--tagless",
        action="store_true",
        help="Include volumes without tags when using --refresh and --tag",
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Refresh existing alarms"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(tag=args.tag, refresh=args.refresh, tagless=args.tagless)
