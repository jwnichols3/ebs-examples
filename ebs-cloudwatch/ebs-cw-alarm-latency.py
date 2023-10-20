#####################################################
#####################################################
#                                                   #
# Converged into the ebs-cw-alarm-manager.py script #
#                                                   #
#####################################################
#####################################################

import boto3
import argparse
import sys
import logging


# Constants
class Config:
    PAGINATOR_COUNT = 100
    SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"  # Consider this the default if --sns-topic is not passed
    SNS_OK_ACTION_ARN = SNS_ALARM_ACTION_ARN  # For simplicity, use same SNS topic for Alarm and OK actions
    INCLUDE_OK_ACTION = False  # If set to False, this will not send the "OK" state change of the alarm to SNS
    ALARM_PREFIX = (
        "ImpairedVol_"  # A clean way to identify these automatically created Alarms.
    )

    ALARM_THRESHOLD_VALUE = 200  # Latecy threshold
    ALARM_EVALUATION_PERIODS = 2  # How many times does the threshold have to breached before setting off the alarm
    ALARM_DATAPOINTS_TO_ALARM = (
        1  # Minimum number of datapoints the alarm needs within the alarm period
    )

    ALARM_EVALUATION_TIME = 60  # Frequency of Alarm Evaluation.
    METRIC_PERIOD = ALARM_EVALUATION_TIME  # Has to tbe the same (for now).
    DEFAULT_REGION = "us-west-2"


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main(tag=None, refresh=False, tagless=False, rename=False):
    """Main function that handles creating and updating CloudWatch Alarms for EBS volumes."""
    ec2, cloudwatch, sns = init_aws_clients()
    updated_alarms = []

    if args.sns_topic:
        Config.SNS_ALARM_ACTION_ARN = args.sns_topic

    if not check_sns_exists(sns):
        logging.error("SNS topic doesn't exist or is not accessible.")
        return

    # Get existing alarm names
    alarm_names = [
        alarm["AlarmName"]
        for page in cloudwatch.get_paginator("describe_alarms").paginate(
            MaxRecords=Config.PAGINATOR_COUNT
        )
        for alarm in page["MetricAlarms"]
    ]

    filter_list = []
    if tag:  # Adjust this part
        filter_list = [
            {
                "Name": f"tag:{tag[0]}",
                "Values": [tag[1]],
            }
        ]

    # Get existing volume IDs
    volume_ids = [
        vol["VolumeId"]
        for page in ec2.get_paginator("describe_volumes").paginate(
            MaxResults=Config.PAGINATOR_COUNT,
            Filters=filter_list,  # Add filters here
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

        alarm_name = construct_alarm_name("Read Latency", tagname, volume_id)

        # Check if an alarm with a similar pattern already exists
        existing_alarm = any(
            name.startswith(f"Read Latency {volume_id}") for name in alarm_names
        )

        if existing_alarm and not rename:
            logging.info(
                f"Alert for volume {volume_id} already exists. Use the --rename option to create a new alarm and remove the existing one."
            )
            continue

        if rename and existing_alarm:
            # Remove the existing alarm
            cloudwatch.delete_alarms(AlarmNames=[alarm_name])

        create_latency_alarm(
            volume_id,
            tagname,
            cloudwatch,
            metric_names=["VolumeTotalReadTime", "VolumeReadOps"],
            threshold=Config.ALARM_THRESHOLD_VALUE,
            evaluation_periods=Config.ALARM_EVALUATION_PERIODS,
            datapoints_to_alarm=Config.ALARM_DATAPOINTS_TO_ALARM,
        )
        updated_alarms.append(volume_id)

    if updated_alarms:
        logging.info(f"Updated alarms for volumes: {', '.join(updated_alarms)}")


def construct_alarm_name(base_name, tagname, volume_id):
    """Constructs the alarm name based on base name, tag, and volume ID."""
    return (
        f"{base_name} {tagname} {volume_id}" if tagname else f"{base_name} {volume_id}"
    )


def init_aws_clients():
    """Initializes and returns AWS service clients."""
    try:
        ec2 = boto3.client("ec2")
        cloudwatch = boto3.client("cloudwatch")
        sns = boto3.client("sns")
        return ec2, cloudwatch, sns
    except Exception as e:
        logging.error(f"Error initializing AWS clients: {e}")
        sys.exit(1)


def check_sns_exists(sns):
    """Checks if the SNS topic exists."""
    try:
        sns.get_topic_attributes(TopicArn=Config.SNS_ALARM_ACTION_ARN)
        return True
    except Exception as e:
        logging.error(f"Error checking SNS topic: {e}")
        return False


def create_latency_alarm(
    volume_id,
    tagname,
    cloudwatch,
    metric_names,
    threshold,
    evaluation_periods,
    datapoints_to_alarm,
):
    """Creates or updates a CloudWatch Alarm for EBS latency."""
    alarm_name = construct_alarm_name("Read Latency", tagname, volume_id)
    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": [Config.SNS_ALARM_ACTION_ARN],
        "EvaluationPeriods": evaluation_periods,
        "DatapointsToAlarm": datapoints_to_alarm,
        "Threshold": threshold,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "Metrics": [
            {
                "Id": "e1",
                "Expression": f"(m1 / m2) * 1000",
                "Label": "Latency",
                "ReturnData": True,
            },
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": metric_names[0],
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": Config.ALARM_EVALUATION_TIME,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
            {
                "Id": "m2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": metric_names[1],
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": Config.ALARM_EVALUATION_TIME,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }
    cloudwatch.put_metric_alarm(**alarm_details)
    logging.info(f"New or updated alarm '{alarm_name}' created for volume {volume_id}")


def parse_args():
    """Parses and returns command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create or update CloudWatch Alarms for EBS latency."
    )
    #    parser.add_argument("--tag", help="Tag name to filter volumes.")
    parser.add_argument(
        "--tag",
        nargs=2,
        metavar=("TagName", "TagValue"),
        help="TagName and TagValue to filter EBS volumes.",
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Refresh existing alarms."
    )
    parser.add_argument(
        "--sns-topic",
        help=f"SNS Topic ARN to notify on alarm or ok. Default is {Config.SNS_ALARM_ACTION_ARN}",
    )
    parser.add_argument(
        "--tagless", action="store_true", help="Include volumes without tags."
    )
    parser.add_argument("--rename", action="store_true", help="Rename existing alarms.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(tag=args.tag, refresh=args.refresh, tagless=args.tagless, rename=args.rename)
