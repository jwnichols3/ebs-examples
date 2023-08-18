import boto3
import argparse
import sys

# Change this to your SNS topic ARN.
SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"
PAGINATION_COUNT = 100  # number of items per Boto3 page call


def check_sns_exists(verbose=False):
    if verbose:
        print(f"Checking if SNS topic {SNS_ALARM_ACTION_ARN} exists...")
    try:
        response = sns.get_topic_attributes(TopicArn=SNS_ALARM_ACTION_ARN)
        return True
    except sns.exceptions.AuthorizationErrorException:
        print(
            "The script does not have the necessary permissions to check if the SNS topic exists."
        )
        sys.exit(1)  # Stop the script here
    except sns.exceptions.NotFoundException:
        try:
            response = sns.list_topics()
            print("The provided SNS ARN does not exist. Here are the existing topics: ")
            for topic in response["Topics"]:
                print(topic["TopicArn"])
            return False
        except sns.exceptions.AuthorizationErrorException:
            print(
                "The script does not have the necessary permissions to list SNS topics."
            )
            sys.exit(1)  # Stop the script here
        except Exception as e:
            print("Failed to list SNS topics: " + str(e))
            sys.exit(1)  # Stop the script here


def create_alarm(volume_id, cloudwatch, verbose=False):
    if not check_sns_exists(verbose):
        print("Alarm creation failed due to invalid SNS ARN.")
        return

    alarm_name = "ImpairedVol_" + volume_id
    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": [SNS_ALARM_ACTION_ARN],
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 1.0,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "IF(m3>0 AND m1+m2==0, 1, 0)",
                "Label": "ImpairedVolume",
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
        # Only consider alarms that end with '_impairedvol'
        if alarm_name.endswith("_impairedvol"):
            volume_id = alarm_name[: -len("_impairedvol")]
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
parser = argparse.ArgumentParser(
    description="Create CloudWatch Alarms for EBS Impaired Volumes."
)
parser.add_argument("--volumeid", help="The new volume ID to create the alarm for")
parser.add_argument("--verbose", action="store_true", help="Print verbsoe output")
parser.add_argument(
    "--impaired-alarm-for-all-volumes",
    action="store_true",
    help="Add impairedvol alarms for all volumes",
)
parser.add_argument(
    "--impaired-alarm-cleanup",
    action="store_true",
    help="Remove impairedvol alarms for non-existent volumes",
)
parser.add_argument(
    "--all",
    action="store_true",
    help="Perform all operations: Add impairedvol alarms for all volumes and remove alarms for non-existent volumes",
)
args = parser.parse_args()

# Create EC2 and CloudWatch clients
ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")
sns = boto3.client("sns")

# Get all volumes using pagination
paginator_vols = ec2.get_paginator("describe_volumes")
volume_ids = []

for page in paginator_vols.paginate(MaxResults=PAGINATION_COUNT):
    for volume in page["Volumes"]:
        volume_ids.append(volume["VolumeId"])

# Get all alarms using pagination
paginator_alarms = cloudwatch.get_paginator("describe_alarms")
alarm_names = []

for page in paginator_alarms.paginate(MaxRecords=PAGINATION_COUNT):
    for alarm in page["MetricAlarms"]:
        alarm_names.append(alarm["AlarmName"])

# If --volumeid is provided, create alarm for this volume
if args.volumeid:
    if "ImpairedVol_" + args.volumeid not in alarm_names:
        print(f"Creating impaired volume alarm for {args.volumeid}")
        create_alarm(args.volumeid, cloudwatch, args.vverbose)
    else:
        print(
            f"Alarm 'ImpairedVol_{args.volumeid}' already exists for volume {args.volumeid}"
        )

# If --impaired-alarm-for-all-volumes is provided, create alarm for all volumes
if args.impaired_alarm_for_all_volumes or args.all:
    for volume_id in volume_ids:
        if args.verbose:
            print(f"Evaluating impaired volume alarm for {volume_id}")
        if ("ImpairedVol_" + volume_id) not in alarm_names:  # Fixed line
            print(f"Creating impaired volume alarm for {volume_id}")
            create_alarm(volume_id, cloudwatch)
        else:
            print(
                f"Alarm 'ImpairedVol_{volume_id}' already exists for volume {volume_id}"  # Fixed line
            )

# If --impaired-alarm-cleanup is provided, remove alarms for non-existent volumes
if args.impaired_alarm_cleanup or args.all:
    cleanup_alarms(volume_ids, alarm_names, cloudwatch)


# If no arguments were provided, display the help message
if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)
