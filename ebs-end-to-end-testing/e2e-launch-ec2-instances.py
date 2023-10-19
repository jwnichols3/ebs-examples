import boto3
import os
import re
import sys
import time
import argparse
import base64
import uuid
from tabulate import tabulate
import logging

KEY_PATH = "~/.ssh"  # Path to SSH private key. The assumption is the file name and the AWS EC2 Key are the same. This is used to show a ssh command to access the Linux instance.


class Config:
    KEY_PATH = "~/.ssh"
    DEFAULT_SC1_VOL_SIZE = 125
    DEFAULT_ST1_VOL_SIZE = 125
    DEFAULT_GP2_VOL_SIZE = 5
    DEFAULT_GP3_VOL_SIZE = 5
    DEFAULT_IO2_VOL_SIZE = 5


def main():
    args = parse_args()
    init_logging(args)

    if args.launchrun_list:
        if args.region:
            # Only list for the specified region
            ec2_client, ec2_resource = initialize_aws_clients(args.region)
            print(f"=== Checking LaunchRuns for region {args.region} ===")
            list_unique_launch_runs(
                ec2_client=ec2_client, ec2_resource=ec2_resource, region=args.region
            )
        else:
            all_unique_launch_runs = []
            # List for all available regions
            ec2_client_for_region_list = boto3.client("ec2", region_name="us-east-1")
            regions = [
                region["RegionName"]
                for region in ec2_client_for_region_list.describe_regions()["Regions"]
            ]
            for region in regions:
                ec2_client, ec2_resource = initialize_aws_clients(region)
                print(f"--- {region}: Checking LaunchRuns")
                unique_launch_runs = list_unique_launch_runs(
                    ec2_client=ec2_client, ec2_resource=ec2_resource, region=region
                )
                # print("\n")
                if unique_launch_runs:
                    all_unique_launch_runs.extend(
                        [(region, launch_run) for launch_run in unique_launch_runs]
                    )

            print("\n=== Summary of All Unique LaunchRuns Across All Regions ===")
            python_executable = sys.executable
            script_name = os.path.basename(__file__)

            for region, launch_run in all_unique_launch_runs:
                print(
                    f"{python_executable} {script_name} --region {region} --terminate {launch_run}"
                )

        return

    if args.region is None:
        region_list = get_region_list()
        if region_list is None:
            region_list = ["us-east-1", "us-east-2", "us-west-2", "eu-west-1"]
        args.region = prompt_for_choice(
            region_list, "Please select a region (by number): "
        )

    ec2_client, ec2_resource = initialize_aws_clients(args.region)

    if args.terminate:
        terminate_instances_by_launch_run(
            launch_run_id=args.terminate,
            ec2_client=ec2_client,
            ec2_resource=ec2_resource,
            no_wait=args.no_wait,
        )
        return

    incoming_params = {
        "ec2_client": ec2_client,
        "ec2_resource": ec2_resource,
        "instance_count": args.instances,
        "volume_count": args.volumes,
        "volume_type": args.vol_type,
        "region": args.region,
        "az": args.az,
        "vpc": args.vpc,
        "security_group": args.sg,
        "key_name": args.key,
        "quiet": args.quiet,
        "clustername": args.clustername,
        "fis_enabled": args.fis_enabled,
        "style": args.style,
    }

    launch_instances(**incoming_params)


def get_user_data_script():
    user_data_script = """#!/bin/bash
yum -y install fio
yum -y install parted

# Get the root partition and the root device
root_partition=$(df --output=source / | tail -1)
root_device=$(echo $root_partition | sed -E 's/p[0-9]+$//')

for device_path in /dev/nvme*n1; do  # Only match NVMe namespaces, not partitions
  # Skip if the device_path is the root device or the root partition
  if [[ "$device_path" != "$root_device" && "$device_path" != "$root_partition" ]]; then
    device_name=$(basename $device_path)
    
    # Create a single partition on the device
    parted $device_path --script mklabel gpt mkpart primary ext4 0% 100%
    
    # Wait a bit for the partition table to get re-read
    sleep 5
    
    # Format the partition to ext4
    mkfs.ext4 "${device_path}p1"
    
    # Create a mount point and mount the partition
    mkdir -p "/mnt/${device_name}"
    mount "${device_path}p1" "/mnt/${device_name}"
    
    # Random read/write I/O
    fio --name=random-rw_${device_name} --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=2m --time_based --runtime=100000h --filename="/mnt/${device_name}/fio_test_file" &

    fio --name=sequential-rw_${device_name} --ioengine=posixaio --rw=rw --bs=128k --numjobs=1 --size=1g --time_based --runtime=100000h --filename="/mnt/${device_name}/fio_test_file" &
  fi
done"""
    return user_data_script


def init_logging(args):
    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def generate_launch_run_id():
    return str(uuid.uuid4())


def initialize_aws_clients(region):
    try:
        ec2_client = boto3.client("ec2", region_name=region)
        ec2_resource = boto3.resource("ec2", region_name=region)
        logging.debug("Initilized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)  # Stop the script here

    return ec2_client, ec2_resource


def terminate_instances_by_launch_run(launch_run_id, ec2_client, ec2_resource, no_wait):
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

    if no_wait:
        logging.info(
            "Not waiting to validate termination of all instances. This can take several minutes."
        )
        return

    all_terminated = False
    while not all_terminated:
        instances = ec2_resource.instances.filter(
            Filters=[{"Name": "tag:LaunchRun", "Values": [launch_run_id]}]
        )
        statuses = [instance.state["Name"] for instance in instances]
        all_terminated = all(status == "terminated" for status in statuses)
        if not all_terminated:
            logging.info("Waiting for all instances to terminate...")
            time.sleep(10)
    logging.info(f"All instances for LaunchRun: {launch_run_id} have been terminated.")


def prompt_for_choice(options, prompt_message, allowed_choices=None):
    while True:
        try:
            for i, option in enumerate(options, 1):
                print(
                    f"{i}. {option if not isinstance(option, tuple) else ' - '.join(option)}"
                )
            choice = int(input(prompt_message)) - 1

            # Check for index out of range
            if choice < 0 or choice >= len(options):
                print(
                    f"Invalid choice. Please select a number between 1 and {len(options)}."
                )
                continue  # Skip the rest of the loop and start over

            selected_option = options[choice]

            if allowed_choices is None or selected_option.lower() in allowed_choices:
                return selected_option
            else:
                print(
                    f"Invalid choice. Allowed choices are: {', '.join(allowed_choices)}"
                )

        except KeyboardInterrupt:
            print("\nCtrl-C pressed. Exiting.")
            sys.exit(0)  # Exit the script

        except ValueError:
            print("Invalid input. Please enter a number.")


def get_key_pairs(ec2_client):
    response = ec2_client.describe_key_pairs()
    return [key_pair["KeyName"] for key_pair in response["KeyPairs"]]


def get_security_groups(ec2_client):
    response = ec2_client.describe_security_groups()
    return [f"{sg['GroupId']} - {sg['GroupName']}" for sg in response["SecurityGroups"]]


def get_vpcs(ec2_client):
    response = ec2_client.describe_vpcs()
    return [vpc["VpcId"] for vpc in response["Vpcs"]]


def get_vpcs_with_names(ec2_client):
    response = ec2_client.describe_vpcs()
    return [
        (vpc["VpcId"], vpc.get("Tags", [{}])[0].get("Value", "N/A"))
        for vpc in response["Vpcs"]
    ]


def get_availability_zones_for_vpc(ec2_client, vpc_id):
    response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    azs = list(set(subnet["AvailabilityZone"] for subnet in response["Subnets"]))
    return azs


def get_availability_zones(ec2_client):
    response = ec2_client.describe_availability_zones()
    return [az["ZoneName"] for az in response["AvailabilityZones"]]


def get_subnets_for_vpc(ec2_client, vpc_id):
    response = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    return [subnet["SubnetId"] for subnet in response["Subnets"]]


def get_availability_zone_for_subnet(ec2_client, subnet_id):
    response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
    return response["Subnets"][0]["AvailabilityZone"]


def get_security_groups_for_vpc(ec2_client, vpc_id):
    response = ec2_client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    return [(sg["GroupId"], sg["GroupName"]) for sg in response["SecurityGroups"]]


def get_subnet_id_for_az_and_vpc(ec2_client, az, vpc_id):
    response = ec2_client.describe_subnets(
        Filters=[
            {"Name": "availability-zone", "Values": [az]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )
    if not response["Subnets"]:
        raise ValueError("No subnet found for the given availability zone and VPC.")
    return response["Subnets"][0]["SubnetId"]


def get_latest_amazon_linux_ami(ec2_client):
    response = ec2_client.describe_images(
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


def get_region_list():
    try:
        with open("region-list.txt", "r") as f:
            return [line.strip() for line in f]
    except FileNotFoundError:
        return None


def validate_sg_and_subnet(ec2_client, security_group, subnet_id):
    sg_response = ec2_client.describe_security_groups(GroupIds=[security_group])
    subnet_response = ec2_client.describe_subnets(SubnetIds=[subnet_id])

    sg_vpc = sg_response["SecurityGroups"][0]["VpcId"]
    subnet_vpc = subnet_response["Subnets"][0]["VpcId"]

    if sg_vpc != subnet_vpc:
        raise ValueError("Security group and subnet belong to different VPCs.")


def list_unique_launch_runs(ec2_client, ec2_resource, region):
    # Fetching instances with LaunchRun tag and in 'running' state
    instances = ec2_resource.instances.filter(
        Filters=[
            {"Name": "tag-key", "Values": ["LaunchRun"]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )

    # Fetching volumes with LaunchRun tag and in 'in-use' state
    response = ec2_client.describe_volumes(
        Filters=[
            {"Name": "tag-key", "Values": ["LaunchRun"]},
            {"Name": "status", "Values": ["in-use"]},
        ]
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
        # print("No active LaunchRuns found.")
        logging.info(f"No active LaunchRuns found in {region}.")
        return
    print("Unique active LaunchRun IDs:")
    for launch_run in unique_launch_runs:
        print(f"- {launch_run}")

    # if logging.debug:
    script_name = os.path.basename(__file__)

    print(f"Terminate launch runs in region {region}:")

    for launch_run_terminate in unique_launch_runs:
        print(f"{script_name} --region {region} --terminate {launch_run_terminate}")

    return unique_launch_runs


def handle_user_inputs(**kwargs):
    instance_count = kwargs.get("instance_count")
    volume_count = kwargs.get("volume_count")
    key_name = kwargs.get("key_name")
    vpc = kwargs.get("vpc")
    az = kwargs.get("az")
    security_group = kwargs.get("security_group")
    ec2_client = kwargs.get("ec2_client")
    vol_type = kwargs.get("vol_type")
    clustername = kwargs.get("clustername")

    if instance_count is None:
        instance_count = int(input("Please enter the number of instances: "))

    if volume_count is None:
        volume_count = int(input("Please enter the number of volumes per instance: "))

    if vol_type is None:
        allowed_vol_types = ["gp2", "gp3", "st1", "sc1", "io2"]
        vol_type = prompt_for_choice(
            allowed_vol_types,
            "Please enter type of volume (by number): ",
            allowed_choices=allowed_vol_types,
        )

    if clustername is None:
        clustername = input("Please enter the cluster name: ")
        # Remove spaces and special characters
        clustername = re.sub(r"[^\w]", "", clustername)
        if not clustername:
            clustername = "NA"
        print(f"ClusterName Tag: {clustername}")

    if key_name is None:
        available_keys = get_key_pairs(ec2_client)
        if available_keys:
            key_name = prompt_for_choice(
                available_keys + ["Create new key pair", "Proceed without key pair"],
                "Please select a key pair (by number): ",
            )
            if key_name == "Create new key pair":
                # Add logic to create a new key pair
                pass
            elif key_name == "Proceed without key pair":
                key_name = None
        else:
            print("No existing key pairs found.")
            create_or_proceed = prompt_for_choice(
                ["Proceed without key pair"],
                "Would you like to proceed without a key pair? (by number): ",
            )
            if create_or_proceed == "Create new key pair":
                # Add logic to create a new key pair
                pass
            elif create_or_proceed == "Proceed without key pair":
                key_name = None

    if vpc is None:
        selected_option = prompt_for_choice(
            get_vpcs_with_names(ec2_client), "Please select a VPC (by number): "
        )
        vpc = selected_option[0]
    if az is None:
        az = prompt_for_choice(
            get_availability_zones_for_vpc(ec2_client, vpc),
            "Please select an availability zone (by number): ",
        )
    if security_group is None:
        selected_option = prompt_for_choice(
            get_security_groups_for_vpc(ec2_client, vpc),
            "Please select a Security Group (by number): ",
        )
        security_group = selected_option[0]

    return_set = {
        "instance_count": instance_count,
        "volume_count": volume_count,
        "key_name": key_name,
        "vpc": vpc,
        "az": az,
        "security_group": security_group,
        "vol_type": vol_type,
        "clustername": clustername,
    }

    return return_set


def prepare_launch_params(**kwargs):
    volume_count = kwargs.get("volume_count")
    ec2_client = kwargs.get("ec2_client")
    az = kwargs.get("az")
    security_group = kwargs.get("security_group")
    vpc = kwargs.get("vpc")
    vol_type = kwargs.get("vol_type", "gp3")
    key_name = kwargs.get("key_name", None)

    ami_id = get_latest_amazon_linux_ami(ec2_client)
    block_device_mappings = []
    volume_size_map = {
        "sc1": Config.DEFAULT_SC1_VOL_SIZE,
        "st1": Config.DEFAULT_ST1_VOL_SIZE,
        "gp2": Config.DEFAULT_GP2_VOL_SIZE,
        "gp3": Config.DEFAULT_GP3_VOL_SIZE,
        "io2": Config.DEFAULT_IO2_VOL_SIZE,
    }

    for i in range(volume_count):
        volume_size = volume_size_map.get(vol_type, 5)
        ebs_config = {
            "VolumeType": vol_type,
            "VolumeSize": volume_size,
        }
        # Add Iops only if volume type is io2
        if vol_type == "io2":
            ebs_config["Iops"] = 125

        block_device_mappings.append(
            {
                "DeviceName": f'/dev/sd{"b" if i == 0 else chr(ord("b") + i)}',
                "Ebs": ebs_config,
            }
        )
    user_data_script = get_user_data_script()
    subnet_id = get_subnet_id_for_az_and_vpc(ec2_client=ec2_client, az=az, vpc_id=vpc)
    validate_sg_and_subnet(
        ec2_client=ec2_client, security_group=security_group, subnet_id=subnet_id
    )
    launch_params = {
        "ImageId": ami_id,
        "InstanceType": "m5.large",
        "MaxCount": 1,
        "MinCount": 1,
        "Placement": {"AvailabilityZone": az},
        "UserData": base64.b64encode(user_data_script.encode()).decode(),
        "BlockDeviceMappings": block_device_mappings,
        "SubnetId": subnet_id,
        "SecurityGroupIds": [security_group],
    }
    if key_name is not None and key_name.lower() != "nokey":
        launch_params["KeyName"] = key_name
    #    if key_name:
    #        launch_params["KeyName"] = key_name

    return launch_params


def monitor_instance_status(
    instance_ids, ec2_client, style, key_name, region, quiet=False
):
    all_running = False
    while not all_running:
        summary_table = []
        for instance_id in instance_ids:
            for _ in range(2):  # Two attempts
                try:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    break  # Exit the loop if successful
                except Exception as e:
                    if _ == 0:  # First attempt
                        time.sleep(10)
                    else:  # Second attempt
                        print(f"Failed to describe instance {instance_id}. Exiting.")
                        print(f"Error: {e}")
                        exit(1)

            instance = response["Reservations"][0]["Instances"][0]
            status = instance["State"]["Name"]
            public_ip = instance.get("PublicIpAddress", "")
            private_ip = instance["PrivateIpAddress"]
            terminate_command = f"aws ec2 terminate-instances --instance-ids {instance_id} --region {region}"
            ssh_command = "No SSH (no key pair)."
            if key_name:
                ssh_command = f"ssh -i {KEY_PATH}/{key_name}.pem ec2-user@{public_ip}"

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
        all_running = all(row[1] == "running" for row in summary_table)
        if not all_running:
            if not quiet:
                print("--- Progress Update ---")
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
            time.sleep(3)
    if not quiet:
        print("=== Summary ===")
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


def launch_instances(**kwargs):
    instance_count = kwargs.get("instance_count", 1)
    volume_count = kwargs.get("volume_count", 1)
    region = kwargs.get("region", "us-west-2")
    az = kwargs.get("az")
    key_name = kwargs.get("key_name", "nokey")
    security_group = kwargs.get("security_group")
    vpc = kwargs.get("vpc")
    style = kwargs.get("style")
    ec2_client = kwargs.get("ec2_client")
    ec2_resource = kwargs.get("ec2_resource")
    quiet = kwargs.get("quiet", False)
    vol_type = kwargs.get("volume_type", "gp3")
    clustername = kwargs.get("clustername")
    fis_enabled = kwargs.get("fis_enabled", False)

    launch_run_id = generate_launch_run_id()
    logging.info(f"LaunchRun ID: {launch_run_id}")
    if quiet:
        print(f"{launch_run_id}")

    user_inputs = {
        "instance_count": instance_count,
        "volume_count": volume_count,
        "key_name": key_name,
        "vpc": vpc,
        "az": az,
        "security_group": security_group,
        "ec2_client": ec2_client,
        "vol_type": vol_type,
        "clustername": clustername,
    }

    returned_user_inputs = handle_user_inputs(**user_inputs)

    instance_count = returned_user_inputs["instance_count"]
    volume_count = returned_user_inputs["volume_count"]
    key_name = returned_user_inputs["key_name"]
    vpc = returned_user_inputs["vpc"]
    az = returned_user_inputs["az"]
    security_group = returned_user_inputs["security_group"]
    vol_type = returned_user_inputs["vol_type"]
    clustername = returned_user_inputs["clustername"]

    launch_params_input = {
        "instance_count": instance_count,
        "volume_count": volume_count,
        "ec2_client": ec2_client,
        "az": az,
        "security_group": security_group,
        "vpc": vpc,
        "key_name": key_name,
        "vol_type": vol_type,
    }
    launch_params = prepare_launch_params(**launch_params_input)

    if fis_enabled:
        fis_key_value = "True"
    else:
        fis_key_value = "False"

    launch_params["TagSpecifications"] = [
        {
            "ResourceType": "instance",
            "Tags": [
                {"Key": "LaunchRun", "Value": launch_run_id},
                {"Key": "ClusterName", "Value": clustername},
                {"Key": "FIS_Chaos", "Value": fis_key_value},
            ],
        },
        {
            "ResourceType": "volume",
            "Tags": [
                {"Key": "LaunchRun", "Value": launch_run_id},
                {"Key": "ClusterName", "Value": clustername},
                {"Key": "FIS_Chaos", "Value": fis_key_value},
            ],
        },
    ]
    instance_ids = []
    for i in range(instance_count):
        response = ec2_client.run_instances(**launch_params)
        instance_id = response["Instances"][0]["InstanceId"]
        instance_ids.append(instance_id)
        logging.info(f"Launched instance {i+1}: {instance_id}")

    monitor_instance_status(
        instance_ids=instance_ids,
        ec2_client=ec2_client,
        style=style,
        key_name=key_name,
        region=region,
        quiet=quiet,
    )

    if logging.info:
        python_executable = sys.executable
        script_name = os.path.basename(__file__)
        key_option = (
            f"--key {key_name}"
            if key_name is not None and key_name.lower() != "nokey"
            else "--key 'nokey'"
        )
        comparable_cli_command = f"{python_executable} {script_name} --instances {instance_count} --volumes {volume_count} --vol-type {vol_type} --region {region} --vpc {vpc} --az {az} --sg {security_group} {key_option} --clustername {clustername}"
        logging.info(f"\nThe LaunchRun for this group is {launch_run_id}\n")
        logging.info(f"\nComparable CLI Command:\n{comparable_cli_command}")

        logging.info(
            f"\n\nTo terminate these instances, run the following command:\n{python_executable} {script_name} --terminate {launch_run_id} --region {region}"
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
    parser.add_argument("--region", type=str, help="AWS region.")
    parser.add_argument("--vpc", type=str, help="VPC ID.")
    parser.add_argument(
        "--vol-type",
        type=lambda x: x.lower(),  # Convert input to lowercase
        choices=["gp2", "gp3", "st1", "sc1", "io2"],  # Define allowed choices
        help="Volume Type (gp2, gp3, st1, sc1, io2)",
    )
    parser.add_argument("--az", type=str, help="AWS availability zone.")
    parser.add_argument("--key", type=str, help="EC2 key pair name.")
    parser.add_argument("--sg", type=str, help="Security group ID.")
    parser.add_argument("--clustername", type=str, help="Cluster name tag.")
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
        "--fis-enabled",
        action="store_true",
        help="Include the FIS_Chaos tag set to True for EC2 and EBS volumes.",
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
    parser.add_argument(
        "--no-wait", action="store_true", help="Do not wait for instances to terminate."
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
