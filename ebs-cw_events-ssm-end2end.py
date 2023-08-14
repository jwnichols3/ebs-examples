import boto3
import time
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

SLEEP_DURATION = 30  # How long to sleep between the creation and deletion
TIME_BETWEEN_SEARCH = 1  # number of seconds between the search for the CW Alarms
DEFAULT_REGION = "us-west-2"


def create_ebs_volume(region, verbose=False):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.create_volume(
        Size=1, VolumeType="gp2", AvailabilityZone=f"{region}a"
    )
    if verbose:
        print(f"Create Volume Response: {response}")
    return response["VolumeId"]


def delete_ebs_volume(region, volume_id, verbose):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.delete_volume(VolumeId=volume_id)

    # Wait for the volume to be deleted
    waiter = ec2.get_waiter("volume_deleted")
    waiter.wait(VolumeIds=[volume_id])

    time_volume_deleted = datetime.now()
    print(f"{time_volume_deleted} - Deleted EBS Volume: {volume_id}")

    return time_volume_deleted


def find_alarm(region, volume_id, wait_for_removal=False, verbose=False):
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    alarm_name = f"ImpairedVol_{volume_id}"
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=2)

    while datetime.now() < end_time:
        alarms = cloudwatch.describe_alarms(AlarmNamePrefix=alarm_name)
        alarm_found = any(
            alarm["AlarmName"] == alarm_name for alarm in alarms["MetricAlarms"]
        )

        if not wait_for_removal and alarm_found:
            time_alarm_found = datetime.now()
            print(f"{time_alarm_found} - Found alarm: {alarm_name}")
            return time_alarm_found

        if wait_for_removal and not alarm_found:
            time_alarm_removed = datetime.now()
            print(f"{time_alarm_removed} - Alarm {alarm_name} no longer exists")
            return time_alarm_removed

        retry_message = (
            "not found, retrying..." if not wait_for_removal else "found, retrying..."
        )
        print(f"{datetime.now()} - Alarm {alarm_name} {retry_message}")
        time.sleep(TIME_BETWEEN_SEARCH)

    print(f"Alarm {alarm_name} was not found within the 2-minute wait period.")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="EBS and CloudWatch Alarms end-to-end test"
    )
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    args = parser.parse_args()

    # Create an EBS volume
    time_created = datetime.now()
    volume_id = create_ebs_volume(args.region, args.verbose)
    print(f"{time_created} - Created EBS Volume: {volume_id}")

    # Wait for the corresponding CloudWatch Alarm
    time_alarm_found = find_alarm(args.region, volume_id, args.verbose)
    if not time_alarm_found:
        print("Alarm not found. Exiting.")
        exit(1)

    # Sleep for 30 seconds
    print(f"{datetime.now()} - Sleeping for {SLEEP_DURATION} seconds")
    time.sleep(SLEEP_DURATION)

    # Delete the EBS volume
    time_deleted = delete_ebs_volume(args.region, volume_id, args.verbose)

    # Check until the CloudWatch Alarm is gone
    time_alarm_removed = find_alarm(
        region=args.region,
        volume_id=volume_id,
        verbose=args.verbose,
        wait_for_removal=True,
    )

    if time_alarm_removed:
        print(f"{datetime.now()} - Finished")

        # Print summary table
        elapsed_creation_time = time_alarm_found - time_created
        elapsed_removal_time = time_alarm_removed - time_deleted
        summary_table = [
            ["Volume ID", volume_id],
            ["Time Created", time_created],
            ["Time Alarm Found", time_alarm_found],
            ["Elapsed Creation Time", elapsed_creation_time],
            ["Time Deleted", time_deleted],
            ["Time Alarm Removed", time_alarm_removed],
            ["Elapsed Removal Time", elapsed_removal_time],
        ]
        print(tabulate(summary_table))


if __name__ == "__main__":
    main()
