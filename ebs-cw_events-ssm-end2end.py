import boto3
import time
from datetime import datetime


def create_ebs_volume():
    ec2 = boto3.client("ec2", region_name="your-region")
    response = ec2.create_volume(
        Size=1, VolumeType="gp2", AvailabilityZone="your-region-a"
    )
    return response["VolumeId"]


def delete_ebs_volume(volume_id):
    ec2 = boto3.client("ec2", region_name="your-region")
    ec2.delete_volume(VolumeId=volume_id)


def find_alarm(volume_id):
    cw = boto3.client("cloudwatch", region_name="your-region")
    alarm_name = f"ImpairedVol_{volume_id}"
    start_time = time.time()
    while time.time() - start_time < 120:
        alarms = cw.describe_alarms(AlarmNamePrefix=alarm_name)
        for alarm in alarms["MetricAlarms"]:
            if alarm["AlarmName"] == alarm_name:
                print(f"{datetime.now()} - Found alarm: {alarm_name}")
                return True
        print(f"{datetime.now()} - Alarm not found, retrying...")
        time.sleep(5)
    print(f"{datetime.now()} - Alarm not found within 2 minutes")
    return False


def main():
    # 1) Create an EBS volume
    volume_id = create_ebs_volume()
    print(f"{datetime.now()} - Created EBS Volume: {volume_id}")

    # 2) Check for the corresponding CloudWatch Alarm
    alarm_found = find_alarm(volume_id)
    if not alarm_found:
        print("Exiting...")
        return

    # 3) Sleep for 30 seconds
    sleep_time = 30
    print(f"{datetime.now()} - Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)

    # 4) Delete the EBS volume
    delete_ebs_volume(volume_id)
    print(f"{datetime.now()} - Deleted EBS Volume: {volume_id}")

    # 5) Check until the CloudWatch Alarm is gone
    start_time = time.time()
    while find_alarm(volume_id) and time.time() - start_time < 120:
        print(f"{datetime.now()} - Waiting for alarm to be removed...")
        time.sleep(5)

    print(f"{datetime.now()} - Finished")


if __name__ == "__main__":
    main()
