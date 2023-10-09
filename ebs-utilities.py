import sys
import argparse
import boto3
import logging
from tabulate import tabulate


def main():
    args = parse_args()

    initialize_logging(args.loglevel)

    ec2, cloudwatch = initialize_aws_clients(region=args.region)

    if args.list_tags:
        if args.volumeid is not None:
            list_volume_tags(ec2=ec2, volume_id=args.volumeid)
        else:
            list_volume_tags(ec2=ec2)

    if args.list_volumes:
        list_volumes(ec2=ec2, style=args.style)

    if args.list_volumes_raw:
        list_all_volumes_raw(ec2=ec2)

    if args.metadata_fields:
        get_all_ebs_metadata_fields(ec2=ec2)

    if args.metadata:
        print_volume_metadata(ec2=ec2)


def get_all_ebs_metadata_fields(ec2):
    volume = next(iter(ec2.volumes.all()), None)

    if volume is None:
        print("No volumes found.")
        return

    for attr in dir(volume):
        if not attr.startswith("__"):
            print(attr)


def get_volume_metadata(volume):
    metadata = {}
    for attr in dir(volume):
        if not attr.startswith("__") and not callable(getattr(volume, attr)):
            metadata[attr] = getattr(volume, attr)
    return metadata


def list_volume_tags(ec2, volume_id=None):
    if volume_id is not None:
        volumes = [ec2.Volume(volume_id)]
    else:
        volumes = list(ec2.volumes.all())

    for volume in volumes:
        if volume.tags is None:
            print(f"Volume {volume.id} does not have any tags.")
            continue

        print(f"Tags for volume {volume.id}:")
        for tag in volume.tags:
            print(f"  Key: {tag['Key']}, Value: {tag['Value']}")
        print("---")


def describe_status(ec2, volume_id):
    volume = ec2.Volume(volume_id)
    status = volume.describe_status()
    print(f"Status for volume {volume_id}:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    print("---")


def print_volume_metadata(ec2):
    for volume in ec2.volumes.all():
        metadata = get_volume_metadata(volume)
        print(f"Metadata for volume {volume.id}:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print("---")


def list_cloudwatch_metrics(volume_id, cloudwatch):
    dimensions = [{"Name": "VolumeId", "Value": volume_id}]
    response = cloudwatch.list_metrics(Dimensions=dimensions)

    if "Metrics" in response:
        for metric in response["Metrics"]:
            print(f"Metric Name: {metric['MetricName']}")
            print(f"Namespace: {metric['Namespace']}")
            print(f"Dimensions: {metric['Dimensions']}")
            print("---")
    else:
        print("No CloudWatch metrics found for the specified EBS volume.")


def list_volumes(ec2, style):
    volumes = ec2.volumes.all()

    table_data = []
    for volume in volumes:
        volume_id = volume.id
        volume_name = volume.tags[0]["Value"] if volume.tags else ""
        status = volume.state
        volume_type = volume.volume_type
        size = volume.size
        date_created = volume.create_time
        attached_instance_id = (
            volume.attachments[0]["InstanceId"] if volume.attachments else ""
        )
        ec2_instance_name = ""
        if attached_instance_id:
            instance = ec2.Instance(attached_instance_id)
            ec2_instance_name = next(
                (tag["Value"] for tag in instance.tags if tag["Key"] == "Name"), ""
            )

        table_data.append(
            [
                volume_id,
                volume_name,
                status,
                volume_type,
                size,
                date_created,
                attached_instance_id,
                ec2_instance_name,
            ]
        )

    print(
        tabulate(
            table_data,
            headers=[
                "volume-id",
                "name",
                "status",
                "type",
                "size",
                "date created",
                "ec2 instance",
                "ec2 name",
            ],
            tablefmt=style,
        )
    )


def list_all_volumes_raw(ec2):
    # Assuming you have AWS credentials set up, otherwise, configure them here
    response = ec2.describe_volumes()

    if "Volumes" in response:
        for volume in response["Volumes"]:
            print(f"Volume ID: {volume['VolumeId']}")
            print(f"Volume Type: {volume['VolumeType']}")
            print(f"Size: {volume['Size']} GB")
            print(f"Status: {volume['State']}")
            print("---")
            describe_status(ec2=ec2, volume_id=volume["VolumeId"])
    else:
        print("No EBS volumes found in the account.")


def initialize_logging(loglevel):
    logging.basicConfig(level=getattr(logging, loglevel.upper()))


def initialize_aws_clients(region):
    try:
        ec2 = boto3.resource("ec2", region_name=region)  # Added this line
        ec2_client = boto3.client("ec2", region_name=region)
        cloudwatch = boto3.client("cloudwatch", region_name=region)
        logging.info("Initialized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)

    return ec2, cloudwatch  # Changed this line


def parse_args():
    parser = argparse.ArgumentParser(description="AWS EBS Utilities")
    parser.add_argument(
        "--list-volumes",
        action="store_true",
        help="List all EBS volumes in the account",
    )
    parser.add_argument(
        "--list-volumes-raw",
        action="store_true",
        help="List all EBS volumes in the account in raw json output",
    )
    parser.add_argument(
        "--style",
        choices=["tsv", "simple", "pretty", "plain", "github", "grid", "fancy"],
        default="simple",
        help="Table style for --list-volumes.",
    )
    parser.add_argument(
        "--region",
        default="us-west-2",  # Default region
        help="AWS region to operate on",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="List tags for all volumes or a specific volume if --volumeid is provided",
    )
    parser.add_argument("--volumeid", help="The volume ID to operate on")
    parser.add_argument(
        "--metadata-fields",
        action="store_true",
        help="List all EBS metadata fields",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Print metadata for all EBS volumes",
    )
    parser.add_argument(
        "--describe-status",
        action="store_true",
        help="Print describe-status metadata for all EBS volumes",
    )
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
