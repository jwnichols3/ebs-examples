import boto3
import time
import argparse
import datetime

# Constants for Default AWS Region - change this to match your environment.
DEFAULT_AWS_REGION = "us-west-2"
# Constants for the SSM Automation Documents - change these to match your environment.
# The assumption is you have these configured in Systems Manager Automation
SSM_CW_ALARM_CREATE = "Rocket-CW-EBS-Alarm-ImpairedVol-Create"
SSM_CW_ALARM_CLEANUP = "Rocket-CW-EBS-Alarm-ImpairedVol-Cleanup"


def run_automation(document_name, region=DEFAULT_AWS_REGION, verbose=False):
    ssm = boto3.client("ssm", region_name=region)

    try:
        response = ssm.start_automation_execution(DocumentName=document_name)
        execution_id = response["AutomationExecutionId"]
        print(
            f"{datetime.datetime.now()} - Started automation execution with ID: {execution_id}"
        )

        # Poll the automation execution status until it's completed
        while True:
            execution_details = ssm.describe_automation_executions(
                Filters=[{"Key": "ExecutionId", "Values": [execution_id]}]
            )
            execution_detail = execution_details["AutomationExecutionMetadataList"][0]
            status = execution_detail["AutomationExecutionStatus"]

            if status in ["Success", "Failed"]:
                print(
                    f"{datetime.datetime.now()} - Automation execution completed with status: {status}"
                )
                break

            # Print the execution details (for verbose mode)
            if verbose:
                print(f"{datetime.datetime.now()} - Current status: {status}")

            time.sleep(10)  # Wait for 10 seconds before checking again

        return status == "Success"
    except Exception as e:
        print(
            f"{datetime.datetime.now()} - An error occurred while running automation: {e}"
        )
        return False


def create_ebs_volume(
    size_gb=10, volume_type="gp2", verbose=False, region=DEFAULT_AWS_REGION
):
    ec2 = boto3.resource("ec2", region_name=region)
    # Specify an availability zone when creating the volume
    availability_zone = region + "a"
    volume = ec2.create_volume(
        Size=size_gb, VolumeType=volume_type, AvailabilityZone=availability_zone
    )
    if verbose:
        print(f"{datetime.datetime.now()} - Creating EBS volume with ID: {volume.id}")

    while volume.state != "available":
        volume.reload()
        if verbose:
            print(
                f"{datetime.datetime.now()} - Volume {volume.id} status: {volume.state}"
            )
        time.sleep(5)

    return volume.id


def delete_ebs_volume(volume_id, region, verbose=False):
    ec2 = boto3.resource("ec2")
    volume = ec2.Volume(volume_id)
    if verbose:
        print(f"{datetime.datetime.now()} - Deleting EBS volume with ID: {volume.id}")
    volume.delete()


def list_cloudwatch_alarms(region, verbose=False):
    cloudwatch = boto3.client("cloudwatch")
    alarms = cloudwatch.describe_alarms()
    print("{datetime.datetime.now()} - List of EBS CloudWatch Alerts:")
    for alarm in alarms["MetricAlarms"]:
        print(alarm["AlarmName"])


def main():
    parser = argparse.ArgumentParser(
        description="Manually run the AWS EBS CloudWatch Alarm Automation. Change the SSM Automation Documents to match your environment."
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed status")
    parser.add_argument(
        "--region",
        default=DEFAULT_AWS_REGION,
        help="AWS region to use (default: {DEFAULT_AWS_REGION})",
    )
    args = parser.parse_args()

    if not run_automation(SSM_CW_ALARM_CREATE, args.region, args.verbose):
        exit(1)
    input("Press any key to continue...")

    volume_id = create_ebs_volume(verbose=args.verbose)
    print(
        f"EBS Volume {volume_id} is available. Running CloudWatch Alarm creation again..."
    )
    run_automation(SSM_CW_ALARM_CREATE, args.region, args.verbose)
    input("Press any key to continue...")

    list_cloudwatch_alarms(args.region, args.verbose)
    input("Press any key to continue...")

    delete_ebs_volume(volume_id, args.region, args.verbose)
    input("Press any key to continue...")

    if not run_automation(SSM_CW_ALARM_CLEANUP, args.region, args.verbose):
        exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
