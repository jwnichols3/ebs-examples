import boto3
import time
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

TIME_BETWEEN_SEARCH = 1  # number of seconds between the search for the CW Alarms


def create_ebs_volume(region, verbose):
    ec2 = boto3.resource("ec2", region_name=region)
    if verbose:
        print(f"Creating EBS Volume")

    volume = ec2.create_volume(Size=10, VolumeType="gp2", AvailabilityZone=f"{region}a")
    volume_id = volume.id

    if verbose:
        print(f"Response: {volume}")

    time_created = datetime.now()
    if verbose:
        print(f"{datetime.now()} - Created EBS Volume: {volume_id}")
    return volume_id, time_created, volume


def delete_ebs_volume(region, volume_id, verbose):
    ec2 = boto3.client("ec2", region_name=region)
    if verbose:
        print(f"Deleting volume {volume_id}")

    response = ec2.delete_volume(VolumeId=volume_id)

    if verbose:
        print(f"Response: {response}")
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
            "not found yet, retrying..."
            if not wait_for_removal
            else "still found, retrying..."
        )
        print(f"{datetime.now()} - Alarm {alarm_name} {retry_message}")
        time.sleep(TIME_BETWEEN_SEARCH)

    print(f"Alarm {alarm_name} was not found within the 2-minute wait period.")
    return None


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="EBS and CloudWatch Events End-to-End Testing"
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed logs")
    parser.add_argument(
        "--region", default="us-west-2", help="AWS region (default: us-west-2)"
    )
    parser.add_argument(
        "--style",
        default="simple",
        choices=["tsv", "simple", "pretty", "plain", "github", "grid", "fancy"],
        help="Table style (tsv, simple, fancy) - default: simple",
    )
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of repetitions (default: 1)"
    )
    parser.add_argument(
        "--sleep_time",
        type=int,
        help="Sleep time in seconds between alarm found and volume delete (default: 5)",
    )
    return parser.parse_args()


def print_summary(args):
    print("Verbose mode: ON")
    print(f"Region: {args.region}")
    print(f"Repeat: {args.repeat}")
    print(f"Sleep time: {args.sleep_time} seconds")
    print(f"Table style: {args.style}")


def main():
    args = parse_arguments()
    summary_table = []

    if args.verbose:
        print_summary(args)

    for i in range(args.repeat):
        print(f"{datetime.now()} - ### Repeating {i+1} of {args.repeat} times ###")
        create_started = datetime.now()
        print(f"{datetime.now()} - Creating EBS Volume.")
        volume_id, time_created, _ = create_ebs_volume(args.region, args.verbose)
        print(
            f"{datetime.now()} - Finding CloudWatch Alarm for ImpairedVol_{volume_id}"
        )
        time_alarm_found = find_alarm(args.region, volume_id, False, args.verbose)
        sleep_time = args.sleep_time if args.sleep_time else 5
        if args.verbose:
            print(f"{datetime.now()} - Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)
        delete_started = datetime.now()
        print(f"{datetime.now()} - Deleting EBS Volume: {volume_id}")
        time_deleted = delete_ebs_volume(args.region, volume_id, args.verbose)

        print(
            f"{datetime.now()} - Waiting for CloudWatch Alarm ImpairedVol_{volume_id} to be removed..."
        )

        time_alarm_removed = find_alarm(
            args.region,
            volume_id,
            True,
            args.verbose,
        )
        elapsed_create_time = time_alarm_found - create_started
        elapsed_delete_time = time_alarm_removed - delete_started
        total_time = time_alarm_removed - create_started
        if args.verbose:
            summary_table.append(
                [
                    volume_id,
                    create_started,
                    time_created,
                    time_alarm_found,
                    elapsed_create_time,
                    delete_started,
                    time_deleted,
                    time_alarm_removed,
                    elapsed_delete_time,
                    total_time,
                ]
            )
        else:
            summary_table.append(
                [
                    volume_id,
                    create_started,
                    elapsed_create_time,
                    delete_started,
                    elapsed_delete_time,
                    total_time,
                ]
            )

    if args.verbose:
        headers = [
            "Volume ID",
            "Create Started",
            "Time Created",
            "Time Alarm Found",
            "Elapsed Create Time",
            "Time Delete Started",
            "Time Deleted",
            "Time Alarm Removed",
            "Elapsed Removal Time",
            "Total Time",
        ]
    else:
        headers = [
            "Volume ID",
            "Create Started",
            "Elapsed Create Time",
            "Delete Started",
            "Elapsed Delete Time",
            "Total Time",
        ]

    print(tabulate(summary_table, headers=headers, tablefmt=args.style))


if __name__ == "__main__":
    main()
