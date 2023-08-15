import boto3
import time
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

SLEEP_DURATION = 5  # How long to sleep between the creation and deletion
TIME_BETWEEN_SEARCH = 0  # number of seconds between the search for the CW Alarms
DEFAULT_REGION = "us-west-2"


def create_ebs_volume(region, verbose):
    ec2 = boto3.resource("ec2", region_name=region)
    volume = ec2.create_volume(Size=10, VolumeType="gp2", AvailabilityZone=f"{region}a")
    volume_id = volume.id
    time_created = datetime.now()
    if verbose:
        print(f"{datetime.now()} - Created EBS Volume: {volume_id}")
    return volume_id, time_created, volume


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
        description="Script to test EBS volume and CloudWatch Alarm creation and deletion."
    )
    parser.add_argument("--region", default="us-west-2", help="AWS Region")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument(
        "--repeat", default=1, type=int, help="Number of times to repeat the test"
    )
    args = parser.parse_args()

    summary_data = []

    for n in range(args.repeat):
        print(f"{datetime.now()} - Repeating {n + 1} of {args.repeat} times.")
        # Create EBS Volume
        volume_id, time_created, _ = create_ebs_volume(args.region, args.verbose)
        print(f"{datetime.now()} - Created EBS Volume: {volume_id}")

        # Wait for CloudWatch Alarm creation
        time_alarm_found = find_alarm(args.region, volume_id, args.verbose)
        print(f"{datetime.now()} - Found alarm: ImpairedVol_{volume_id}")

        # Sleep for specified time
        print(f"{datetime.now()} - Sleeping for {SLEEP_DURATION} seconds")
        time.sleep(SLEEP_DURATION)

        # Delete EBS Volume
        time_deleted = delete_ebs_volume(args.region, volume_id, args.verbose)
        print(f"{datetime.now()} - Deleted EBS Volume: {volume_id}")

        # Wait for CloudWatch Alarm removal
        time_alarm_removed = find_alarm(args.region, volume_id, True, args.verbose)
        print(f"{datetime.now()} - Alarm ImpairedVol_{volume_id} removed")

        # Collect summary data
        summary_data.append(
            {
                "Volume ID": volume_id,
                "Time Created": time_created,
                "Time Alarm Found": time_alarm_found,
                "Elapsed Create Time": time_alarm_found - time_created,
                "Time Deleted": time_deleted,
                "Time Alarm Removed": time_alarm_removed,
                "Elapsed Removal Time": time_alarm_removed - time_deleted,
            }
        )

    # Print summary table
    headers = [
        "Volume ID",
        "Time Created",
        "Time Alarm Found",
        "Elapsed Create Time",
        "Time Deleted",
        "Time Alarm Removed",
        "Elapsed Removal Time",
    ]
    table_data = [list(item.values()) for item in summary_data]
    print(tabulate(table_data, headers=headers, tablefmt="simple"))


if __name__ == "__main__":
    main()
