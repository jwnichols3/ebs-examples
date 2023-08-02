import sys
import argparse
import boto3


def get_all_ebs_metadata_fields():
    ec2 = boto3.resource("ec2")
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


def describe_status(volume_id):
    ec2 = boto3.resource("ec2")
    volume = ec2.Volume(volume_id)
    status = volume.describe_status()
    print(f"Status for volume {volume_id}:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    print("---")


def print_volume_metadata():
    ec2 = boto3.resource("ec2")

    for volume in ec2.volumes.all():
        metadata = get_volume_metadata(volume)
        print(f"Metadata for volume {volume.id}:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print("---")


def list_cloudwatch_metrics(volume_id):
    # Assuming you have AWS credentials set up, otherwise, configure them here
    cloudwatch_client = boto3.client("cloudwatch")

    dimensions = [{"Name": "VolumeId", "Value": volume_id}]
    response = cloudwatch_client.list_metrics(Dimensions=dimensions)

    if "Metrics" in response:
        for metric in response["Metrics"]:
            print(f"Metric Name: {metric['MetricName']}")
            print(f"Namespace: {metric['Namespace']}")
            print(f"Dimensions: {metric['Dimensions']}")
            print("---")
    else:
        print("No CloudWatch metrics found for the specified EBS volume.")


def list_all_volumes():
    # Assuming you have AWS credentials set up, otherwise, configure them here
    ec2_client = boto3.client("ec2")
    response = ec2_client.describe_volumes()

    if "Volumes" in response:
        for volume in response["Volumes"]:
            print(f"Volume ID: {volume['VolumeId']}")
            print(f"Volume Type: {volume['VolumeType']}")
            print(f"Size: {volume['Size']} GB")
            print(f"Status: {volume['State']}")
            print("---")
            describe_status(volume["VolumeId"])
    else:
        print("No EBS volumes found in the account.")


def main():
    parser = argparse.ArgumentParser(description="AWS EBS Utilities")
    parser.add_argument(
        "--list-volumes",
        action="store_true",
        help="List all EBS volumes in the account",
    )
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
    args = parser.parse_args()

    if args.list_volumes:
        list_all_volumes()

    if args.metadata_fields:
        get_all_ebs_metadata_fields()

    if args.metadata:
        print_volume_metadata()


if __name__ == "__main__":
    main()
