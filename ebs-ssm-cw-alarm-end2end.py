import boto3
import time
import argparse


def run_automation(automation_name, verbose):
    ssm = boto3.client("ssm")
    response = ssm.start_automation_execution(DocumentName=automation_name)
    execution_id = response["AutomationExecutionId"]

    while True:
        status_response = ssm.describe_automation_executions(
            Filters=[{"Key": "ExecutionId", "Values": [execution_id]}]
        )
        status = status_response["AutomationExecutionMetadataList"][0][
            "AutomationExecutionStatus"
        ]
        if verbose:
            print(f"Automation {automation_name} status: {status}")
        if status in ["Success", "Failed", "Cancelled"]:
            break
        time.sleep(10)

    if status == "Success":
        if verbose:
            print(f"Automation {automation_name} succeeded.")
        return True
    else:
        print(f"Automation {automation_name} failed with status {status}.")
        print(status_response["AutomationExecutionMetadataList"][0]["FailureMessage"])
        return False


def create_ebs_volume(size_gb=10, volume_type="gp2", verbose=False):
    ec2 = boto3.resource("ec2")
    volume = ec2.create_volume(Size=size_gb, VolumeType=volume_type)
    if verbose:
        print(f"Creating EBS volume with ID: {volume.id}")

    while volume.state != "available":
        volume.reload()
        if verbose:
            print(f"Volume {volume.id} status: {volume.state}")
        time.sleep(5)

    return volume.id


def delete_ebs_volume(volume_id, verbose=False):
    ec2 = boto3.resource("ec2")
    volume = ec2.Volume(volume_id)
    if verbose:
        print(f"Deleting EBS volume with ID: {volume.id}")
    volume.delete()


def list_cloudwatch_alarms(verbose=False):
    cloudwatch = boto3.client("cloudwatch")
    alarms = cloudwatch.describe_alarms()
    print("List of EBS CloudWatch Alerts:")
    for alarm in alarms["MetricAlarms"]:
        print(alarm["AlarmName"])


def main():
    parser = argparse.ArgumentParser(description="AWS EBS CloudWatch Alarm Automation")
    parser.add_argument("--verbose", action="store_true", help="Print detailed status")
    args = parser.parse_args()

    if not run_automation("Rocket-CW-EBS-Alarm-ImpairedVol-Create", args.verbose):
        exit(1)
    input("Press any key to continue...")

    volume_id = create_ebs_volume(verbose=args.verbose)
    print(
        f"EBS Volume {volume_id} is available. Running CloudWatch Alarm creation again..."
    )
    run_automation("Rocket-CW-EBS-Alarm-ImpairedVol-Create", args.verbose)
    input("Press any key to continue...")

    list_cloudwatch_alarms(args.verbose)
    input("Press any key to continue...")

    delete_ebs_volume(volume_id, args.verbose)
    input("Press any key to continue...")

    if not run_automation("Rocket-CW-EBS-Alarm-ImpairedVol-Cleanup", args.verbose):
        exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
