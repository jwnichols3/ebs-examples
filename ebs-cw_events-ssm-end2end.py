import boto3
import time
import argparse
from datetime import datetime


def create_ebs_volume(region, verbose=False):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.create_volume(
        Size=1, VolumeType="gp2", AvailabilityZone=f"{region}a"
    )
    if verbose:
        print(f"Create Volume Response: {response}")
    return response["VolumeId"]


def delete_ebs_volume(region, volume_id, verbose=False):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.delete_volume(VolumeId=volume_id)
    if verbose:
        print(f"Delete Volume Response: {response}")


def find_alarm(region, volume_id, verbose=False):
    cw = boto3.client("cloudwatch", region_name=region)
    alarm_name = f"ImpairedVol_{volume_id}"
    start_time = time.time()
    while time.time() - start_time < 120:
        response = cw.describe_alarms(AlarmNamePrefix=alarm_name)
        if verbose:
            print(f"Describe Alarms Response: {response}")
        for alarm in response["MetricAlarms"]:
            if alarm["AlarmName"] == alarm_name:
                print(f"{datetime.now()} - Found alarm: {alarm_name}")
                return True
        print(f"{datetime.now()} - Alarm not found, retrying...")
        time.sleep(5)
    print(f"{datetime.now()} - Alarm not found within 2 minutes")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="EBS Volume and CloudWatch Alarm Automation"
    )
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # 1) Create an EBS volume
    volume_id = create_ebs_volume(args.region, args.verbose)
    print(f"{datetime.now()} - Created EBS Volume: {volume_id}")

    # 2) Check for the corresponding CloudWatch Alarm
    alarm_found = find_alarm(args.region, volume_id, args.verbose)
    if not alarm_found:
        print("Exiting...")
        return

    # 3) Sleep for 30 seconds
    sleep_time = 30
    print(f"{datetime.now()} - Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)

    # 4) Delete the EBS volume
    delete_ebs_volume(args.region, volume_id, args.verbose)
    print(f"{datetime.now()} - Deleted EBS Volume: {volume_id}")

    # 5) Check until the CloudWatch Alarm is gone
    start_time = time.time()
    while (
        find_alarm(args.region, volume_id, args.verbose)
        and time.time() - start_time < 120
    ):
        print(f"{datetime.now()} - Waiting for alarm to be removed...")
        time.sleep(5)

    print(f"{datetime.now()} - Finished")


if __name__ == "__main__":
    main()
