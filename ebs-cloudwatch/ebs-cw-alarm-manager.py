import boto3
import argparse
import sys
import logging


# Make changes to how you want the alarm parameters in this class.
class Config:
    PAGINATION_COUNT = 100  # EBS Get volume pagination count
    DEFAULT_REGION = "us-west-2"
    INCLUDE_OK_ACTION = True  # If set to False, this will not send the "OK" state change of the alarm to SNS
    SNS_OK_ACTION_ARN = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"  # Consider this the default if --sns-topic is not passed
    SNS_ALARM_ACTION_ARN = (
        SNS_OK_ACTION_ARN  # For simplicity, use same SNS topic for Alarm and OK actions
    )
    ## ImpairedVol Settings ##
    ALARM_IMPAIREDVOL_NAME_PREFIX = "EBS_ImpairedVol_"  # A clean way to identify these automatically created Alarms.
    ALARM_IMPAIREDVOL_EVALUATION_TIME = 60  # Frequency of Alarm Evaluation.
    ALARM_IMPAIREDVOL_METRIC_PERIOD = (
        ALARM_IMPAIREDVOL_EVALUATION_TIME  # Has to tbe the same (for now).
    )
    ALARM_IMPAIREDVOL_EVALUATION_PERIODS = 2  # How many times does the threshold have to breached before setting off the alarm
    ALARM_IMPAIREDVOL_DATAPOINTS_TO_ALARM = (
        2  # Minimum number of datapoints the alarm needs within the alarm period
    )
    ALARM_IMPAIREDVOL_THRESHOLD_VALUE = 1  # Threshold value for alarm
    ## ReadLatency Settings ##
    ALARM_READLATENCY_NAME_PREFIX = "EBS_ReadLatency_"  # A clean way to identify these automatically created Alarms.
    ALARM_READLATENCY_THRESHOLD_VALUE = 50  # Threshold value for alarm
    ALARM_READLATENCY_EVALUATION_TIME = 60  # Frequency of Alarm Evaluation.
    ALARM_READLATENCY_METRIC_PERIOD = (
        ALARM_READLATENCY_EVALUATION_TIME  # Has to tbe the same (for now).
    )
    ALARM_READLATENCY_EVALUATION_PERIODS = 2  # How many times does the threshold have to breached before setting off the alarm
    ALARM_READLATENCY_DATAPOINTS_TO_ALARM = (
        2  # Minimum number of datapoints the alarm needs within the alarm period
    )
    ## WriteLatency Settings ##
    ALARM_WRITELATENCY_NAME_PREFIX = "EBS_WriteLatency_"  # A clean way to identify these automatically created Alarms.
    ALARM_WRITELATENCY_THRESHOLD_VALUE = 200  # Threshold value for alarm
    ALARM_WRITELATENCY_EVALUATION_TIME = 60  # Frequency of Alarm Evaluation.
    ALARM_WRITELATENCY_METRIC_PERIOD = (
        ALARM_WRITELATENCY_EVALUATION_TIME  # Has to tbe the same (for now).
    )
    ALARM_WRITELATENCY_EVALUATION_PERIODS = 2  # How many times does the threshold have to breached before setting off the alarm
    ALARM_WRITELATENCY_DATAPOINTS_TO_ALARM = (
        2  # Minimum number of datapoints the alarm needs within the alarm period
    )


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
    # if --tag is used, it requires two values passed (tag_name, tag_value)
    tag_name, tag_value = args.tag if args.tag else (None, None)
    volume_ids = get_volume_ids(ec2=ec2, tag_name=tag_name, tag_value=tag_value)
    alarm_names = get_all_alarm_names(cloudwatch=cloudwatch)

    stats = {"created": 0, "deleted": 0, "volumes_processed": 0}
    volumes_without_alarm = []

    if args.sns_topic:
        Config.SNS_ALARM_ACTION_ARN = args.sns_topic
        Config.SNS_OK_ACTION_ARN = args.sns_topic

    alarm_type = args.alarm_type

    # Check SNS existence here only for --all and --create
    if args.create:
        if not check_sns_exists(sns=sns, sns_topic_arn=Config.SNS_ALARM_ACTION_ARN):
            logging.error(
                f"Invalid SNS ARN provided: {Config.SNS_ALARM_ACTION_ARN}. Exiting."
            )
            sys.exit(1)  # Stop the script here

        if Config.INCLUDE_OK_ACTION and not check_sns_exists(
            sns=sns, sns_topic_arn=Config.SNS_OK_ACTION_ARN
        ):
            logging.error(
                f"Invalid SNS ARN provided: {Config.SNS_OK_ACTION_ARN}. Exiting."
            )
            sys.exit(1)  # Stop the script here

    if alarm_type == "all":
        alarm_types_list = ["impairedvol", "readlatency", "writelatency"]
    else:
        alarm_types_list = [alarm_type]

    if args.create:
        for alarm_type in alarm_types_list:
            stats["created"] += create_alarms(
                target_volumes=volume_ids,
                alarm_names=alarm_names,
                cloudwatch=cloudwatch,
                ec2=ec2,
                alarm_type=alarm_type,
            )

    if args.cleanup:
        for alarm_type in alarm_types_list:
            stats["deleted"] += cleanup_alarms(
                volume_ids=volume_ids,
                alarm_names=alarm_names,
                cloudwatch=cloudwatch,
                alarm_type=alarm_type,
            )

    print(
        f"Volumes Processed: {len(volume_ids)}, Alarms Created: {stats['created']}, Alarms Deleted: {stats['deleted']}"
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

    #### Launch Run is a setting used by the e2e-launch-ec2-instances.py script in this repo.
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


def get_volume_ids(ec2, tag_name=None, tag_value=None):
    paginator = ec2.get_paginator("describe_volumes")
    volume_ids = []

    filter_args = []
    if tag_name and tag_value:
        filter_args.append({"Name": f"tag:{tag_name}", "Values": [tag_value]})

    for page in paginator.paginate(
        Filters=filter_args, MaxResults=Config.PAGINATION_COUNT
    ):
        for volume in page["Volumes"]:
            volume_ids.append(volume["VolumeId"])
    logging.debug(f"Volume IDs:\n{volume_ids}")
    return volume_ids


def cleanup_alarms(volume_ids, alarm_names, cloudwatch, alarm_type):
    deleted_count = 0

    if alarm_type == "impairedvol":
        search_prefix = Config.ALARM_IMPAIREDVOL_NAME_PREFIX
    if alarm_type == "readlatency":
        search_prefix = Config.ALARM_READLATENCY_NAME_PREFIX
    if alarm_type == "writelatency":
        search_prefix = Config.ALARM_WRITELATENCY_NAME_PREFIX

    for alarm_name in alarm_names:
        # Only consider alarms that start with 'ImpairedVol_'
        if alarm_name.startswith(search_prefix):
            # Extract volume ID from the alarm name
            volume_id = alarm_name[len(search_prefix) :]

            if volume_id not in volume_ids:
                logging.info(
                    f"Deleting {alarm_type} alarm {alarm_name} as volume {volume_id} no longer exists"
                )
                try:
                    cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                    deleted_count += 1
                except cloudwatch.exceptions.ClientError as e:
                    logging.error(
                        f"Failed to delete {alarm_type} alarm {alarm_name}: {e}"
                    )
                except Exception as e:
                    logging.error(f"Unknown error when deleting {alarm_name}: {e}")

            else:
                logging.info(
                    f"No change to {alarm_type} alarm {alarm_name} as volume {volume_id} still exists"
                )

    return deleted_count


def generate_alarm_name(volume_id, alarm_type):
    if alarm_type == "impairedvol":
        return Config.ALARM_IMPAIREDVOL_NAME_PREFIX + volume_id
    if alarm_type == "readlatency":
        return Config.ALARM_READLATENCY_NAME_PREFIX + volume_id
    if alarm_type == "writelatency":
        return Config.ALARM_WRITELATENCY_NAME_PREFIX + volume_id


def create_alarms(target_volumes, alarm_names, cloudwatch, ec2, alarm_type):
    created_count = 0
    for volume_id in target_volumes:
        alarm_name = generate_alarm_name(volume_id=volume_id, alarm_type=alarm_type)
        if alarm_name not in alarm_names:
            create_alarm(
                volume_id=volume_id,
                cloudwatch=cloudwatch,
                ec2=ec2,
                alarm_name=alarm_name,
                alarm_type=alarm_type,
            )
            created_count += 1
        else:
            logging.info(f"CW Alarm {alarm_name} already exists.")

    return created_count


def create_alarm(volume_id, cloudwatch, ec2, alarm_name, alarm_type):
    alarm_description = generate_alarm_description(volume_id=volume_id, ec2=ec2)

    alarm_details = {
        "AlarmName": alarm_name,
        "AlarmActions": [Config.SNS_ALARM_ACTION_ARN],
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "TreatMissingData": "missing",
        "AlarmDescription": alarm_description,
    }

    if alarm_type == "impairedvol":
        alarm_details.update(get_impairedvol_alarm_params(volume_id))
    if alarm_type == "readlatency":
        alarm_details.update(get_readlatency_alarm_params(volume_id))
    if alarm_type == "writelatency":
        alarm_details.update(get_writelatency_alarm_params(volume_id))

    if Config.INCLUDE_OK_ACTION:
        alarm_details.update(
            {
                "OKActions": [Config.SNS_OK_ACTION_ARN],
            }
        )

    logging.debug(f"CloudWatch JSON:\n{alarm_details}\n")
    logging.info(f"Creating {alarm_type} alarm {alarm_name} for volume {volume_id}.")

    # Create the new alarm
    try:
        if Config.INCLUDE_OK_ACTION:
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
            f"New {alarm_type} alarm '{alarm_details['AlarmName']}' created for volume {volume_id}"
        )
    except cloudwatch.exceptions.ClientError as error:
        logging.error(
            f"Error creating alarm {alarm_name} for volume {volume_id}: {error}"
        )
    except Exception as e:
        logging.error(
            f"Unexpected error creating alarm {alarm_name} for volume {volume_id}: {e}"
        )


def get_readlatency_alarm_params(volume_id):
    return {
        "EvaluationPeriods": Config.ALARM_READLATENCY_EVALUATION_PERIODS,
        "DatapointsToAlarm": Config.ALARM_READLATENCY_DATAPOINTS_TO_ALARM,
        "Threshold": Config.ALARM_READLATENCY_THRESHOLD_VALUE,
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "(m1 / m2) * 1000",
                "Label": "Latency",
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
                    "Period": Config.ALARM_READLATENCY_METRIC_PERIOD,
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
                    "Period": Config.ALARM_READLATENCY_EVALUATION_TIME,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }


def get_writelatency_alarm_params(volume_id):
    return {
        "EvaluationPeriods": Config.ALARM_WRITELATENCY_EVALUATION_PERIODS,
        "DatapointsToAlarm": Config.ALARM_WRITELATENCY_DATAPOINTS_TO_ALARM,
        "Threshold": Config.ALARM_WRITELATENCY_THRESHOLD_VALUE,
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "(m1 / m2) * 1000",
                "Label": "Latency",
                "ReturnData": True,
            },
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeTotalWriteTime",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": Config.ALARM_WRITELATENCY_METRIC_PERIOD,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
            {
                "Id": "m2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeWriteOps",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": Config.ALARM_WRITELATENCY_EVALUATION_TIME,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }


def get_impairedvol_alarm_params(volume_id):
    return {
        "EvaluationPeriods": Config.ALARM_IMPAIREDVOL_EVALUATION_PERIODS,
        "DatapointsToAlarm": Config.ALARM_IMPAIREDVOL_DATAPOINTS_TO_ALARM,
        "Threshold": Config.ALARM_IMPAIREDVOL_THRESHOLD_VALUE,
        "Metrics": [
            {
                "Id": "e1",
                "Expression": "IF(m3>0 AND m1+m2==0, 1, 0)",
                "Label": "ImpairedVolume",
                "ReturnData": True,
                "Period": Config.ALARM_IMPAIREDVOL_EVALUATION_TIME,
            },
            {
                "Id": "m3",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EBS",
                        "MetricName": "VolumeQueueLength",
                        "Dimensions": [{"Name": "VolumeId", "Value": volume_id}],
                    },
                    "Period": Config.ALARM_IMPAIREDVOL_METRIC_PERIOD,
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
                    "Period": Config.ALARM_IMPAIREDVOL_METRIC_PERIOD,
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
                    "Period": Config.ALARM_IMPAIREDVOL_METRIC_PERIOD,
                    "Stat": "Average",
                },
                "ReturnData": False,
            },
        ],
    }


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


def get_all_alarm_names(cloudwatch):
    paginator = cloudwatch.get_paginator("describe_alarms")
    alarm_names = []
    for page in paginator.paginate(MaxRecords=Config.PAGINATION_COUNT):
        for alarm in page["MetricAlarms"]:
            alarm_names.append(alarm["AlarmName"])
    logging.debug(f"Volume IDs:\n{alarm_names}")
    return alarm_names


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Alarms for EBS Impaired Volumes."
    )
    parser.add_argument("--volume-id", help="Specific volume id to operate on.")
    parser.add_argument(
        "--sns-topic",
        help=f"SNS Topic ARN to notify on alarm or ok. Default is {Config.SNS_ALARM_ACTION_ARN}",
    )
    parser.add_argument(
        "--alarm-type",
        type=lambda x: x.lower(),
        choices=["all", "impairedvol", "readlatency", "writelatency"],
        help=f"Which alarm type to process. Options are All, ImpairedVol, ReadLatency, and WriteLatency. Default is All.",
    )
    parser.add_argument(
        "--create", action="store_true", help="Create CloudWatch Alarms."
    )
    parser.add_argument(
        "--tag",
        nargs=2,
        metavar=("TagName", "TagValue"),
        help="TagName and TagValue to filter EBS volumes.",
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Cleanup CloudWatch Alarms."
    )
    parser.add_argument(
        "--region",
        default=Config.DEFAULT_REGION,
        help=f"AWS Region (defaults to {Config.DEFAULT_REGION}).",
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
