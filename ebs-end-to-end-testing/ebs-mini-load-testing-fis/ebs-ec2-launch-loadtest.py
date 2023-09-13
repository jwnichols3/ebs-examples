import boto3
import time
import argparse
import base64
from tabulate import tabulate

KEY_PATH = "~/.ssh"  # Path to SSH private key


def prompt_for_choice(options, prompt_message):
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
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


def get_availability_zones_for_vpc(region, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    azs = list(set(subnet["AvailabilityZone"] for subnet in response["Subnets"]))
    return azs


def get_availability_zones(region):
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_availability_zones()
    return [az["ZoneName"] for az in response["AvailabilityZones"]]


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


def launch_instances(
    instances, volumes, region, az, key_name, security_group, vpc, style
):
    ec2 = boto3.client("ec2", region_name=region)

    if key_name is None:
        key_name = prompt_for_choice(
            get_key_pairs(region), "Please select a key pair (by number): "
        )

    if security_group is None:
        selected_option = prompt_for_choice(
            get_security_groups(region), "Please select a security group (by number): "
        )
        security_group = selected_option.split(" ")[0]

    # Prompt for VPC if not provided
    if vpc is None:
        vpc = prompt_for_choice(get_vpcs(region), "Please select a VPC (by number): ")

    # Prompt for AZ if not provided
    if az is None:
        az = prompt_for_choice(
            get_availability_zones_for_vpc(region, vpc),
            "Please select an availability zone (by number): ",
        )

    ami_id = get_latest_amazon_linux_ami(region)

    block_device_mappings = []
    for i in range(volumes):
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

    launch_params = {
        "ImageId": ami_id,
        "InstanceType": "m5.large",
        "MaxCount": 1,
        "MinCount": 1,
        "Placement": {"AvailabilityZone": az},
        "UserData": base64.b64encode(user_data_script.encode()).decode(),
        "BlockDeviceMappings": block_device_mappings,
    }

    if key_name:
        launch_params["KeyName"] = key_name

    if security_group:
        launch_params["SecurityGroupIds"] = [security_group]

    instance_ids = []
    for i in range(instances):
        response = ec2.run_instances(**launch_params)
        instance_id = response["Instances"][0]["InstanceId"]
        instance_ids.append(instance_id)
        print(f"Launched instance {instance_id}")

    print("\nMonitoring instance status:")

    all_running = False
    while not all_running:
        summary_table = []
        for instance_id in instance_ids:
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

        print(
            tabulate(
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

    print("\nSummary:")
    print(
        tabulate(
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


def main():
    parser = argparse.ArgumentParser(
        description="Launch EC2 instances with EBS volumes and start load testing."
    )
    parser.add_argument(
        "--instances", type=int, default=10, help="Number of EC2 instances to launch."
    )
    parser.add_argument(
        "--volumes", type=int, default=10, help="Number of EBS volumes per instance."
    )
    parser.add_argument("--region", type=str, default="us-west-2", help="AWS region.")
    parser.add_argument("--vpc", type=str, help="VPC ID.")
    parser.add_argument("--az", type=str, help="AWS availability zone.")
    parser.add_argument("--key", type=str, help="EC2 key pair name.")
    parser.add_argument("--sg", type=str, help="Security group ID.")
    parser.add_argument(
        "--style", type=str, default="plain", help="Table style for tabulate."
    )

    args = parser.parse_args()
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


if __name__ == "__main__":
    main()
