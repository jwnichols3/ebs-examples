import boto3
import botocore.exceptions
import os
import sys
import time
import argparse
import base64
import uuid
from tabulate import tabulate
import logging

KEY_PATH = "~/.ssh"  # Path to SSH private key


def main():
    args = parse_args()
    init_logging(args)

    if args.launchrun_list:
        list_unique_launch_runs(args.region)
        return

    if args.terminate:
        terminate_instances_by_launch_run(args.terminate, args.region)
        return

    launch_instances(
        args.instances,
        args.volumes,
        args.region,
        args.az,
        args.key,
        args.sg,
        args.vpc,
        args.style,
    )


def init_logging(args):
    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def generate_launch_run_id():
    return str(uuid.uuid4())


def terminate_instances_by_launch_run(launch_run_id, region):
    ec2_resource = boto3.resource("ec2", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)  # For volume operations

    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "tag:LaunchRun", "Values": [launch_run_id]}]
    )
    instance_ids = [instance.id for instance in instances]

    if not instance_ids:
        logging.info(f"No instances found for LaunchRun: {launch_run_id}")
        return

    response = ec2_client.describe_volumes(  # Using ec2_client here
        Filters=[{"Name": "tag:LaunchRun", "Values": [launch_run_id]}]
    )
    volume_ids = [volume["VolumeId"] for volume in response["Volumes"]]

    if logging.info:
        print("\n\nTerminating the following EC2 Instances and EBS Volumes:")
        print(f"EC2 Instances: {', '.join(instance_ids)}")
        print(f"EBS Volumes: {', '.join(volume_ids)}")

    ec2_resource.instances.filter(InstanceIds=instance_ids).terminate()
    logging.info(f"\nTerminated instances for LaunchRun: {launch_run_id}")


def prompt_for_choice(options, prompt_message):
    for i, option in enumerate(options, 1):
        print(f"{i}. {option if not isinstance(option, tuple) else ' - '.join(option)}")
    choice = int(input(prompt_message)) - 1
    return options[choice]


def get_key_pairs(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_key_pairs()
    return [key_pair["KeyName"] for key_pair in response["KeyPairs"]]


def get_security_groups(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_security_groups()
    return [f"{sg['GroupId']} - {sg['GroupName']}" for sg in response["SecurityGroups"]]


def get_vpcs(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_vpcs()
    return [vpc["VpcId"] for vpc in response["Vpcs"]]


def get_vpcs_with_names(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_vpcs()
    return [
        (vpc["VpcId"], vpc.get("Tags", [{}])[0].get("Value", "N/A"))
        for vpc in response["Vpcs"]
    ]


def get_availability_zones_for_vpc(region, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    azs = list(set(subnet["AvailabilityZone"] for subnet in response["Subnets"]))
    return azs


def get_availability_zones(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_availability_zones()
    return [az["ZoneName"] for az in response["AvailabilityZones"]]


def get_subnets_for_vpc(region, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    return [subnet["SubnetId"] for subnet in response["Subnets"]]


def get_availability_zone_for_subnet(region, subnet_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_subnets(SubnetIds=[subnet_id])
    return response["Subnets"][0]["AvailabilityZone"]


def get_security_groups_for_vpc(region, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    return [(sg["GroupId"], sg["GroupName"]) for sg in response["SecurityGroups"]]


def get_subnet_id_for_az_and_vpc(region, az, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_subnets(
        Filters=[
            {"Name": "availability-zone", "Values": [az]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )
    if not response["Subnets"]:
        raise ValueError("No subnet found for the given availability zone and VPC.")
    return response["Subnets"][0]["SubnetId"]


def get_latest_amazon_linux_ami(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_images(
        Filters=[
            {"Name": "name", "Values": ["amzn2-ami-hvm-*"]},
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "virtualization-type", "Values": ["hvm"]},
            {"Name": "owner-alias", "Values": ["amazon"]},
            {"Name": "state", "Values": ["available"]},
        ],
        Owners=["amazon"],
    )
    amis = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
    return amis[0]["ImageId"]


def validate_sg_and_subnet(ec2, security_group, subnet_id):
    sg_response = ec2.describe_security_groups(GroupIds=[security_group])
    subnet_response = ec2.describe_subnets(SubnetIds=[subnet_id])

    sg_vpc = sg_response["SecurityGroups"][0]["VpcId"]
    subnet_vpc = subnet_response["Subnets"][0]["VpcId"]

    if sg_vpc != subnet_vpc:
        raise ValueError("Security group and subnet belong to different VPCs.")


def list_unique_launch_runs(region):
    ec2 = boto3.resource("ec2", region_name=region)

    # Fetching instances with LaunchRun tag
    instances = ec2.instances.filter(
        Filters=[{"Name": "tag-key", "Values": ["LaunchRun"]}]
    )

    # Fetching volumes with LaunchRun tag
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_volumes(
        Filters=[{"Name": "tag-key", "Values": ["LaunchRun"]}]
    )

    unique_launch_runs = set()

    # Extracting LaunchRun IDs from instances
    for instance in instances:
        for tag in instance.tags:
            if tag["Key"] == "LaunchRun":
                unique_launch_runs.add(tag["Value"])

    # Extracting LaunchRun IDs from volumes
    for volume in response["Volumes"]:
        for tag in volume["Tags"]:
            if tag["Key"] == "LaunchRun":
                unique_launch_runs.add(tag["Value"])

    if not unique_launch_runs:
        print("No LaunchRuns found.")
        logging.error("No LaunchRuns found.")
        return
    print("Unique LaunchRun IDs:")
    for launch_run in unique_launch_runs:
        print(f"- {launch_run}")


def launch_instances(
    instance_count, volume_count, region, az, key_name, security_group, vpc, style
):
    ec2 = boto3.client("ec2", region_name=region)
    launch_run_id = generate_launch_run_id()
    logging.info(f"LaunchRun ID: {launch_run_id}")
    if logging.error:
        print(f"{launch_run_id}")

    if instance_count is None:
        instance_count = int(input("Please enter the number of instances: "))

    if volume_count is None:
        volume_count = int(input("Please enter the number of volumes per instance: "))

    if key_name is None:
        key_name = prompt_for_choice(
            get_key_pairs(region), "Please select a key pair (by number): "
        )

    # Prompt for VPC if not provided
    if vpc is None:
        selected_option = prompt_for_choice(
            get_vpcs_with_names(region), "Please select a VPC (by number): "
        )
        vpc = selected_option[0]

    all_subnets = get_subnets_for_vpc(region, vpc)

    # Prompt for AZ if not provided
    if az is None:
        az = prompt_for_choice(
            get_availability_zones_for_vpc(region, vpc),
            "Please select an availability zone (by number): ",
        )

    # Get all security groups for the chosen VPC
    all_security_groups = get_security_groups_for_vpc(region, vpc)
    # Prompt for Security Group if not provided

    if security_group is None:
        selected_option = prompt_for_choice(
            all_security_groups, "Please select a Security Group (by number): "
        )
        security_group = selected_option[0]  # Assuming selected_option is now a tuple

    subnet_id = get_subnet_id_for_az_and_vpc(region, az, vpc)

    ami_id = get_latest_amazon_linux_ami(region)

    block_device_mappings = []
    for i in range(volume_count):
        block_device_mappings.append(
            {
                "DeviceName": f'/dev/sd{"b" if i == 0 else chr(ord("b") + i)}',
                "Ebs": {
                    "VolumeType": "gp3",
                    "VolumeSize": 10,
                },
            }
        )

    user_data_script = """#!/bin/bash
yum -y install fio
for device_path in /dev/nvme1n*; do
  # Random read/write I/O
  fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=4 --size=1g --time_based --filename=$device_path &
  # Sequential read/write I/O
  fio --name=sequential-rw --ioengine=posixaio --rw=rw --bs=128k --numjobs=4 --size=1g --time_based --filename=$device_path &
  # Random write I/O
  fio --name=random-write --ioengine=posixaio --rw=randwrite --bs=4k --numjobs=4 --size=1g --time_based --filename=$device_path &
  # Random read I/O
  fio --name=random-read --ioengine=posixaio --rw=randread --bs=4k --numjobs=4 --size=1g --time_based --filename=$device_path &
done"""

    validate_sg_and_subnet(ec2, security_group, subnet_id)

    launch_params = {
        "ImageId": ami_id,
        "InstanceType": "m5.large",
        "MaxCount": 1,
        "MinCount": 1,
        "Placement": {"AvailabilityZone": az},
        "UserData": base64.b64encode(user_data_script.encode()).decode(),
        "BlockDeviceMappings": block_device_mappings,
    }

    launch_params["TagSpecifications"] = [
        {
            "ResourceType": "instance",
            "Tags": [
                {"Key": "LaunchRun", "Value": launch_run_id},
            ],
        },
        {
            "ResourceType": "volume",
            "Tags": [
                {"Key": "LaunchRun", "Value": launch_run_id},
            ],
        },
    ]

    launch_params["SubnetId"] = subnet_id

    if key_name:
        launch_params["KeyName"] = key_name

    if security_group:
        launch_params["SecurityGroupIds"] = [security_group]

    instance_ids = []
    for i in range(instance_count):
        response = ec2.run_instances(**launch_params)
        instance_id = response["Instances"][0]["InstanceId"]
        instance_ids.append(instance_id)
        print(f"Launched instance {instance_id}")

    print("\nMonitoring instance status:")

    all_running = False
    while not all_running:
        summary_table = []
        for instance_id in instance_ids:
            max_retries = 10
            retries = 0

            while retries < max_retries:
                try:
                    response = ec2.describe_instances(InstanceIds=[instance_id])
                    break  # Successful describe, break the loop
                except botocore.exceptions.ClientError as e:
                    if "InvalidInstanceID.NotFound" in str(e):
                        logging.info(
                            f"Instance {instance_id} not found yet, retrying..."
                        )
                        time.sleep(5)
                        retries += 1
                    else:
                        raise  # Any other exception should be raised

            response = ec2.describe_instances(InstanceIds=[instance_id])
            instance = response["Reservations"][0]["Instances"][0]
            status = instance["State"]["Name"]
            public_ip = instance.get("PublicIpAddress", "")
            private_ip = instance["PrivateIpAddress"]
            terminate_command = (
                f"aws ec2 terminate-instances --instance-ids {instance_id}"
            )
            ssh_command = (
                f"ssh -i {KEY_PATH}/{key_name}.pem ec2-user@{public_ip}"
                if public_ip
                else ""
            )
            summary_table.append(
                (
                    instance_id,
                    status,
                    public_ip,
                    private_ip,
                    terminate_command,
                    ssh_command,
                )
            )

        logging.info(
            "\n--- Progress Update ---\n"
            + tabulate(
                summary_table,
                headers=[
                    "Instance ID",
                    "Status",
                    "Public IP",
                    "Private IP",
                    "Terminate Command",
                    "SSH Command",
                ],
                tablefmt=style,
            )
        )

        all_running = all(row[1] == "running" for row in summary_table)

        if not all_running:  # Only sleep if not all instances are running
            time.sleep(10)

    logging.info(
        "\n=== Summary ===\n"
        + tabulate(
            summary_table,
            headers=[
                "Instance ID",
                "Status",
                "Public IP",
                "Private IP",
                "Terminate Command",
                "SSH Command",
            ],
            tablefmt=style,
        )
    )
    if logging.info:
        python_executable = sys.executable
        script_name = os.path.basename(__file__)
        print("\n\nTo terminate these instances, run the following command:")
        print(f"{python_executable} {script_name} --terminate {launch_run_id}")
        print("\n\nTo re-launch instances with the same configuration:")
        print(
            f"{python_executable} {script_name} --instances {instance_count} --volumes {volume_count} --region {region} --az {az} --key {key_name} --sg {security_group} --vpc {vpc}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch EC2 instances with EBS volumes and start load testing."
    )
    parser.add_argument(
        "--instances", type=int, help="Number of EC2 instances to launch."
    )
    parser.add_argument(
        "--volumes", type=int, help="Number of EBS volumes per instance."
    )
    parser.add_argument("--region", type=str, default="us-west-2", help="AWS region.")
    parser.add_argument("--vpc", type=str, help="VPC ID.")
    parser.add_argument("--az", type=str, help="AWS availability zone.")
    parser.add_argument("--key", type=str, help="EC2 key pair name.")
    parser.add_argument("--sg", type=str, help="Security group ID.")
    parser.add_argument(
        "--style", type=str, default="plain", help="Table style for tabulate."
    )
    parser.add_argument(
        "--terminate", type=str, help="Terminate instances by LaunchRun ID."
    )
    parser.add_argument(
        "--launchrun-list", action="store_true", help="List all unique LaunchRun IDs."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output the LaunchRun value if successful.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print out all existing statements."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Output debug information."
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
