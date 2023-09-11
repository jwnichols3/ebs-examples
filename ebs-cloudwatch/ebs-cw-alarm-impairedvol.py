import boto3
import argparse
import sys
import logging

# Change this to your SNS topic ARN.
SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"
PAGINATION_COUNT = 100  # number of items per Boto3 page call


def main():
    args = parse_args()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    ec2, cloudwatch, sns = initialize_aws_clients()
    volume_ids = get_all_volume_ids(ec2)
    alarm_names = get_all_alarm_names(cloudwatch)

    # When --all and --update flags are both provided
    if args.all and args.update:
        logging.info("All Alarms Update Description")
        for volume_id in volume_ids:
            # handle_single_volume(volume_id, alarm_names, cloudwatch, ec2, sns, args)
            handle_update(volume_id, cloudwatch, ec2, args)
        return  # Exit after performing all actions

    # Handle individual flags
    if args.volumeid:
        logging.info("Volume ID")
        handle_single_volume(args.volumeid, alarm_names, cloudwatch, ec2, sns, args)
        if args.update:
            handle_update(args.volumeid, cloudwatch, ec2, args)

    if args.impaired_alarm_for_all_volumes or args.impaired_alarm_cleanup or args.all:
        logging.info("Clean Up Alerts first")
        cleanup_alarms(volume_ids, alarm_names, cloudwatch)
        logging.info("All Volumes Create Alarm")
        for volume_id in volume_ids:
            handle_single_volume(volume_id, alarm_names, cloudwatch, ec2, sns, args)

    if args.impaired_alarm_cleanup and args.all:
        logging.info("All Alarms Cleanup")
        cleanup_alarms(volume_ids, alarm_names, cloudwatch)

    if args.update and not args.all:
        logging.info("Update all alarm descriptions")
        for volume_id in volume_ids:
            handle_update(volume_id, cloudwatch, ec2, args)


def initialize_aws_clients():
    try:
        ec2 = boto3.client("ec2")
        cloudwatch = boto3.client("cloudwatch")
        sns = boto3.client("sns")
        logging.info("Initilized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)  # Stop the script here

    return ec2, cloudwatch, sns


def get_all_volume_ids(ec2):
    paginator = ec2.get_paginator("describe_volumes")
    volume_ids = []
    for page in paginator.paginate(MaxResults=PAGINATION_COUNT):
        for volume in page["Volumes"]:
            volume_ids.append(volume["VolumeId"])
    logging.debug(f"Volume IDs:\n{volume_ids}")
    return volume_ids


def get_all_alarm_names(cloudwatch):
    paginator = cloudwatch.get_paginator("describe_alarms")
    alarm_names = []
    for page in paginator.paginate(MaxRecords=PAGINATION_COUNT):
        for alarm in page["MetricAlarms"]:
            alarm_names.append(alarm["AlarmName"])
    logging.debug(f"Volume IDs:\n{alarm_names}")
    return alarm_names


def handle_single_volume(volume_id, alarm_names, cloudwatch, ec2, sns, args):
    alarm_name = "ImpairedVol_" + volume_id
    if alarm_name not in alarm_names:
        create_alarm(volume_id, cloudwatch, ec2, sns, args.verbose)
    else:
        logging.info(f"Alarm '{alarm_name}' already exists for volume {volume_id}")
        if args.update:
            logging.info(f"Updating Alarm '{alarm_name}' volume {volume_id}")
            update_alarm_description(volume_id, cloudwatch, ec2, args.verbose)


def handle_update(volume_id, cloudwatch, ec2, args):
    try:
        update_alarm_description(volume_id, cloudwatch, ec2, args.verbose)
    except Exception as e:
        logging.error(
            f"An error occurred while updating alarm for volume {volume_id}: {e}"
        )


def check_sns_exists(sns, verbose=False):
    logging.info(f"Checking if SNS topic {SNS_ALARM_ACTION_ARN} exists...")
    try:
        response = sns.get_topic_attributes(TopicArn=SNS_ALARM_ACTION_ARN)
        return True
    except sns.exceptions.AuthorizationErrorException:
        logging.error(
            f"The script does not have the necessary permissions to check if the SNS topic at ARN {SNS_ALARM_ACTION_ARN} exists."
        )
        sys.exit(1)  # Stop the script here
    except sns.exceptions.NotFoundException:
        try:
            response = sns.list_topics()
            logging.error(
                "The provided SNS ARN does not exist. Here are the existing topics: "
            )
            for topic in response["Topics"]:
                logging.error(topic["TopicArn"])
            return False
        except sns.exceptions.AuthorizationErrorException:
            logging.error(
                "The script does not have the necessary permissions to list SNS topics."
            )
            sys.exit(1)  # Stop the script here
        except Exception as e:
            logging.error("Failed to list SNS topics: " + str(e))
            sys.exit(1)  # Stop the script here


def create_alarm(volume_id, cloudwatch, ec2, sns, verbose=False):
    if not check_sns_exists(sns, verbose):
        logging.error(
            f"Alarm creation failed due to invalid SNS ARN. Provided: {SNS_ALARM_ACTION_ARN}"
        )
        return

    # Fetch additional information about the EBS volume
    response = ec2.describe_volumes(VolumeIds=[volume_id])
    volume_info = response["Volumes"][0]
    tags = volume_info.get("Tags", [])
    availability_zone = volume_info["AvailabilityZone"]

    # Convert tags to a string format suitable for inclusion in the alarm description
    tag_string = ", ".join([f"{tag['Key']}:{tag['Value']}" for tag in tags])

    # Create a more detailed alarm description
    alarm_description = (
        f"Alarm for EBS volume {volume_id} in {availability_zone}. Tags: {tag_string}"
    )

    alarm_name = "ImpairedVol_" + volume_id
    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": [SNS_ALARM_ACTION_ARN],
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 1.0,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "AlarmDescription": alarm_description,
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
        AlarmDescription=alarm_details["AlarmDescription"],
        EvaluationPeriods=alarm_details["EvaluationPeriods"],
        DatapointsToAlarm=alarm_details["DatapointsToAlarm"],
        Threshold=alarm_details["Threshold"],
        ComparisonOperator=alarm_details["ComparisonOperator"],
        TreatMissingData=alarm_details["TreatMissingData"],
        Metrics=alarm_details["Metrics"],
    )

    logging.info(
        f"New alarm '{alarm_details['AlarmName']}' created for volume {volume_id}"
    )


def cleanup_alarms(volume_ids, alarm_names, cloudwatch):
    for alarm_name in alarm_names:
        # Only consider alarms that start with 'ImpairedVol_'
        if alarm_name.startswith("ImpairedVol_"):
            # Extract volume ID from the alarm name
            volume_id = alarm_name[len("ImpairedVol_") :]

            if volume_id not in volume_ids:
                logging.info(
                    f"Deleting alarm {alarm_name} as volume {volume_id} no longer exists"
                )
                cloudwatch.delete_alarms(AlarmNames=[alarm_name])
            else:
                logging.info(
                    f"No change to alarm {alarm_name} as volume {volume_id} still exists"
                )


def update_alarm_description(volume_id, cloudwatch, ec2, verbose=False):
    new_description = fetch_volume_info(volume_id, ec2, verbose)

    if new_description is None:
        return

    alarm_name = "ImpairedVol_" + volume_id

    try:
        existing_alarm = cloudwatch.describe_alarms(AlarmNames=[alarm_name])[
            "MetricAlarms"
        ][0]

        # Only update if the description has changed
        if existing_alarm["AlarmDescription"] != new_description:
            existing_alarm["AlarmDescription"] = new_description
            cloudwatch.put_metric_alarm(**existing_alarm)
            logging.info(f"Updated description for alarm {alarm_name}")
        else:
            logging.info(f"The Alarm description for {alarm_name} has not changed.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")


def fetch_volume_info(volume_id, ec2, verbose=False):
    try:
        # Fetch additional information about the EBS volume
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        volume_info = response["Volumes"][0]
        tags = volume_info.get("Tags", [])
        availability_zone = volume_info["AvailabilityZone"]

        # Convert tags to a string format suitable for inclusion in the alarm description
        tag_string = ", ".join([f"{tag['Key']}:{tag['Value']}" for tag in tags])

        # Create a more detailed alarm description
        new_description = f"Alarm for EBS volume {volume_id} in {availability_zone}. Tags: {tag_string}"

        logging.info(f"Fetched information for volume {volume_id}: {new_description}")

        return new_description
    except Exception as e:
        logging.error(
            f"An error occurred while fetching information for volume {volume_id}: {e}"
        )
        return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create CloudWatch Alarms for EBS Impaired Volumes."
    )
    parser.add_argument(
        "--volumeid",
        help="The volume id to create or update the Impaired Volume CloudWatch Alert.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output (logging of INFO level)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug level output (logging of DEBUG level)",
    )
    parser.add_argument(
        "--impaired-alarm-for-all-volumes",
        action="store_true",
        help="Add Impaired Volume alarms for all volumes",
    )
    parser.add_argument(
        "--impaired-alarm-cleanup",
        action="store_true",
        help="Remove Impaired Volume alarms for non-existent volumes",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Perform create and remove operations: Add Impaired Volume alarms for all volumes and remove alarms for non-existent volumes",
    )
    parser.add_argument(
        "--update", action="store_true", help="Update alarm descriptions"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
