import boto3
import argparse
import sys
import logging

# Constants
INCLUDE_OK_ACTION = False  # If set to False, this will not send the "OK" state change of the alarm to SNS
SNS_OK_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"  # You only need to set this if the INCLUDE_OK_ACTION is True
SNS_ALARM_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"
PAGINATION_COUNT = 100
ALARM_EVALUATION_TIME = 60
METRIC_PERIOD = ALARM_EVALUATION_TIME  # Has to tbe the same (for now).


def main():
    args = parse_args()

    # Initialize logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    ec2, cloudwatch, sns = initialize_aws_clients(args.region)
    volume_ids = get_all_volume_ids(ec2=ec2)
    alarm_names = get_all_alarm_names(cloudwatch=cloudwatch)

    stats = {"created": 0, "updated": 0, "deleted": 0, "volumes_processed": 0}
    volumes_without_alarm = []

    # Check SNS existence here only for --all and --create
    if args.all or args.create:
        if not check_sns_exists(sns=sns, sns_topic_arn=SNS_ALARM_ACTION_ARN):
            logging.error(f"Invalid SNS ARN provided: {SNS_ALARM_ACTION_ARN}. Exiting.")
            sys.exit(1)  # Stop the script here

        if INCLUDE_OK_ACTION and not check_sns_exists(
            sns=sns, sns_topic_arn=SNS_OK_ACTION_ARN
        ):
            logging.error(f"Invalid SNS ARN provided: {SNS_OK_ACTION_ARN}. Exiting.")
            sys.exit(1)  # Stop the script here

    if args.all:
        stats["deleted"] = cleanup_alarms(
            volume_ids=volume_ids, alarm_names=alarm_names, cloudwatch=cloudwatch
        )
        stats["created"] = create_alarms(
            target_volumes=volume_ids,
            alarm_names=alarm_names,
            cloudwatch=cloudwatch,
            ec2=ec2,
        )
        stats["updated"] = update_alarms(
            volume_ids=volume_ids,
            cloudwatch=cloudwatch,
            ec2=ec2,
            volumes_without_alarm=volumes_without_alarm,
        )
    else:
        if args.cleanup:
            stats["deleted"] = cleanup_alarms(
                volume_ids=volume_ids, alarm_names=alarm_names, cloudwatch=cloudwatch
            )
        if args.create:
            target_volumes = [args.volume_id] if args.volume_id else volume_ids
            stats["created"] = create_alarms(
                target_volumes=target_volumes,
                alarm_names=alarm_names,
                cloudwatch=cloudwatch,
                ec2=ec2,
            )
        if args.update:
            stats["updated"] = update_alarms(
                volume_ids=volume_ids,
                cloudwatch=cloudwatch,
                ec2=ec2,
                volumes_without_alarm=volumes_without_alarm,
            )

    print(
        f"Volumes Processed: {len(volume_ids)}, Alarms Created: {stats['created']}, Alarms Updated: {stats['updated']}, Alarms Deleted: {stats['deleted']}"
    )
    if volumes_without_alarm:
        print(
            f"The following volume(s) do not have an Impaired Volume Alarm: {', '.join(volumes_without_alarm)}"
        )


def generate_alarm_description(volume_id, ec2):
    volume_details = fetch_volume_info(volume_id=volume_id, ec2=ec2)

    volume_id = volume_details.get("volume_id", "N/A")
    availability_zone = volume_details.get("availability_zone", "N/A")
    tags_dict = volume_details.get("tags_dict", {})
    attached_instance_id = volume_details.get("attached_instance_id", "")
    attached_instance_name = volume_details.get("attached_instance_name", "")

    alarm_description = f"Alarm for EBS volume {volume_id} in {availability_zone}."

    launch_run_tag = tags_dict.get("LaunchRun", "")
    if launch_run_tag:
        alarm_description += f"\nLaunchRun: {launch_run_tag}"
    else:
        tag_string = ", ".join([f"{k}:{v}" for k, v in tags_dict.items()])
        alarm_description += f"\nTags: {tag_string}"

    if attached_instance_id and attached_instance_name:
        alarm_description += f"\nAttached to Instance ID: {attached_instance_id}, Instance Name: {attached_instance_name}"
    elif attached_instance_id:
        alarm_description += f"\nAttached to Instance ID: {attached_instance_id}"

    return alarm_description


def initialize_aws_clients(region):
    try:
        ec2 = boto3.client("ec2", region_name=region)
        cloudwatch = boto3.client("cloudwatch", region_name=region)
        sns = boto3.client("sns", region_name=region)
        logging.info(f"Initilized AWS Client in region {region}")
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
        create_alarm(volume_id=volume_id, cloudwatch=cloudwatch, ec2=ec2, sns=sns)
    else:
        logging.info(f"Alarm '{alarm_name}' already exists for volume {volume_id}")
        if args.update:
            logging.info(f"Updating Alarm '{alarm_name}' volume {volume_id}")
            update_alarm_description(
                volume_id=volume_id, cloudwatch=cloudwatch, ec2=ec2
            )


def handle_update(volume_id, cloudwatch, ec2):
    try:
        update_alarm_description(volume_id=volume_id, cloudwatch=cloudwatch, ec2=ec2)
    except Exception as e:
        logging.error(
            f"An error occurred while updating alarm for volume {volume_id}: {e}"
        )


def check_sns_exists(sns, sns_topic_arn):
    logging.info(f"Checking if SNS topic {sns_topic_arn} exists...")
    try:
        response = sns.get_topic_attributes(TopicArn=sns_topic_arn)
        return True
    except sns.exceptions.AuthorizationErrorException:
        logging.error(
            f"The script does not have the necessary permissions to check if the SNS topic at ARN {sns_topic_arn} exists."
        )
        sys.exit(1)  # Stop the script here
    except sns.exceptions.NotFoundException:
        try:
            response = sns.list_topics()
            logging.error(
                f"The provided SNS ARN {sns_topic_arn} does not exist. Here are the existing topics: "
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


def update_alarms(volume_ids, cloudwatch, ec2, volumes_without_alarm):
    updated_count = 0
    for volume_id in volume_ids:
        if update_alarm_description(
            volume_id=volume_id,
            cloudwatch=cloudwatch,
            ec2=ec2,
            volumes_without_alarm=volumes_without_alarm,
        ):  # Assume it returns True if updated
            updated_count += 1
    return updated_count


def cleanup_alarms(volume_ids, alarm_names, cloudwatch):
    deleted_count = 0

    for alarm_name in alarm_names:
        # Only consider alarms that start with 'ImpairedVol_'
        if alarm_name.startswith("ImpairedVol_"):
            # Extract volume ID from the alarm name
            volume_id = alarm_name[len("ImpairedVol_") :]

            if volume_id not in volume_ids:
                logging.info(
                    f"Deleting alarm {alarm_name} as volume {volume_id} no longer exists"
                )
                try:
                    cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                    deleted_count += 1
                except cloudwatch.exceptions.ClientError as e:
                    logging.error(f"Failed to delete alarm {alarm_name}: {e}")
                except Exception as e:
                    logging.error(f"Unknown error when deleting {alarm_name}: {e}")

            else:
                logging.info(
                    f"No change to alarm {alarm_name} as volume {volume_id} still exists"
                )

    return deleted_count


def create_alarms(target_volumes, alarm_names, cloudwatch, ec2):
    created_count = 0
    for volume_id in target_volumes:
        alarm_name = "ImpairedVol_" + volume_id
        if alarm_name not in alarm_names:
            create_alarm(volume_id=volume_id, cloudwatch=cloudwatch, ec2=ec2)
            created_count += 1
        else:
            logging.info(f"CW Alarm {alarm_name} already exists.")
    return created_count


def create_alarm(volume_id, cloudwatch, ec2):
    alarm_description = generate_alarm_description(volume_id=volume_id, ec2=ec2)

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
                "Period": ALARM_EVALUATION_TIME,
            },
            {
                "Id": "m3",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeQueueLength",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": METRIC_PERIOD,
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
                    "Period": METRIC_PERIOD,
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
                    "Period": METRIC_PERIOD,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }
    if INCLUDE_OK_ACTION:
        alarm_details.append = {
            "OKActions": [SNS_OK_ACTION_ARN],
        }

    logging.info(f"Creating alarm {alarm_name} for volume {volume_id}.")

    # Create the new alarm
    try:
        if INCLUDE_OK_ACTION:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm_details["AlarmName"],
                OKActions=alarm_details["OKActions"],
                AlarmActions=alarm_details["AlarmActions"],
                AlarmDescription=alarm_details["AlarmDescription"],
                EvaluationPeriods=alarm_details["EvaluationPeriods"],
                DatapointsToAlarm=alarm_details["DatapointsToAlarm"],
                Threshold=alarm_details["Threshold"],
                ComparisonOperator=alarm_details["ComparisonOperator"],
                TreatMissingData=alarm_details["TreatMissingData"],
                Metrics=alarm_details["Metrics"],
            )
        else:
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
    except cloudwatch.exceptions.ClientError as error:
        logging.error(
            f"Error creating alarm {alarm_name} for volume {volume_id}: {error}"
        )
    except Exception as e:
        logging.error(
            f"Unexpected error creating alarm {alarm_name} for volume {volume_id}: {e}"
        )


def update_alarm_description(volume_id, cloudwatch, ec2, volumes_without_alarm=None):
    new_description = generate_alarm_description(volume_id=volume_id, ec2=ec2)

    if new_description is None:
        return False  # Indicate that the update was not successful

    alarm_name = "ImpairedVol_" + volume_id

    try:
        existing_alarms = cloudwatch.describe_alarms(AlarmNames=[alarm_name])[
            "MetricAlarms"
        ]
        if len(existing_alarms) == 0:
            logging.error(f"Alarm {alarm_name} not found.")
            volumes_without_alarm.append(volume_id)
            return False

        existing_alarm = existing_alarms[0]
    except cloudwatch.exceptions.ResourceNotFoundException:
        logging.error(f"Alarm {alarm_name} not found.")
        return False
    except cloudwatch.exceptions.ClientError as e:
        logging.error(f"Failed to describe alarm {alarm_name}: {str(e)}")
        return False
    except Exception as e:
        logging.error(
            f"An unknown error occurred while describing alarm {alarm_name}: {str(e)}"
        )
        return False

    # Only update if the description has changed
    if existing_alarm["AlarmDescription"] != new_description:
        existing_alarm["AlarmDescription"] = new_description

        # Only keep the keys that are actually needed for put_metric_alarm
        valid_keys = [
            "AlarmName",
            "AlarmDescription",
            "ActionsEnabled",
            "OKActions",
            "AlarmActions",
            "InsufficientDataActions",
            "MetricName",
            "Namespace",
            "Statistic",
            "ExtendedStatistic",
            "Period",
            "Unit",
            "EvaluationPeriods",
            "DatapointsToAlarm",
            "Threshold",
            "ComparisonOperator",
            "TreatMissingData",
            "EvaluateLowSampleCountPercentile",
            "Metrics",
            "Tags",
            "ThresholdMetricId",
        ]
        filtered_alarm = {
            k: existing_alarm[k] for k in valid_keys if k in existing_alarm
        }

        # Remove Dimensions if Metrics is set
        if "Metrics" in filtered_alarm:
            filtered_alarm.pop("Dimensions", None)

        try:
            cloudwatch.put_metric_alarm(**filtered_alarm)
            logging.info(f"Updated description for alarm {alarm_name}")
            return True  # Indicate that the update was successful
        except cloudwatch.exceptions.ClientError as e:
            logging.error(
                f"Failed to update alarm description for {alarm_name}: {str(e)}"
            )
        except Exception as e:
            logging.error(
                f"An unknown error occurred while updating alarm description for {alarm_name}: {str(e)}"
            )
        return False  # Indicate that the update was not successful
    else:
        logging.info(f"The Alarm description for {alarm_name} has not changed.")
        return False  # Indicate that no update was necessary


def fetch_volume_info(volume_id, ec2):
    try:
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        volume_info = response["Volumes"][0]
        tags = volume_info.get("Tags", [])
        availability_zone = volume_info["AvailabilityZone"]

        tags_dict = {tag["Key"]: tag["Value"] for tag in tags}

        # Fetching attached EC2 instance ID and name
        attachments = volume_info.get("Attachments", [])
        instance_id = ""
        instance_name = ""

        if attachments:
            instance_id = attachments[0].get("InstanceId", "")

            if instance_id:
                instance_response = ec2.describe_instances(InstanceIds=[instance_id])
                instance_info = instance_response["Reservations"][0]["Instances"][0]
                instance_tags = instance_info.get("Tags", [])

                for tag in instance_tags:
                    if tag["Key"] == "Name":
                        instance_name = tag["Value"]
                        break

        volume_details = {
            "volume_id": volume_id,
            "tags_dict": tags_dict,
            "availability_zone": availability_zone,
            "attached_instance_id": instance_id,
            "attached_instance_name": instance_name,
        }

        logging.debug(f"Fetched information for volume {volume_id}: {volume_details}")
        return volume_details
    except Exception as e:
        logging.error(
            f"An error occurred while fetching information for volume {volume_id}: {e}"
        )
        return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Alarms for EBS Impaired Volumes."
    )
    parser.add_argument("--volume-id", help="Specific volume id to operate on.")
    parser.add_argument(
        "--create", action="store_true", help="Create CloudWatch Alarms."
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Cleanup CloudWatch Alarms."
    )
    parser.add_argument(
        "--update", action="store_true", help="Update CloudWatch Alarms."
    )
    parser.add_argument(
        "--region", default="us-west-2", help="AWS Region (defaults to us-west-2)."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Perform cleanup, create, and update operations.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    parser.add_argument("--debug", action="store_true", help="Debug logging.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
