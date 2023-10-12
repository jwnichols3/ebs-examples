import boto3
import csv
import tempfile
import shutil
import argparse
import os
import sys
import logging

# CONSTANTS
EBS_PAGINATION = 300
DEFAULT_REGION = "us-west-2"
DEFAULT_S3_REGION = "us-west-2"
DEFAULT_S3_BUCKET_NAME = "jnicmazn-ebs-observability-us-west-2"
DEFAULT_S3_KEY_PREFIX = ""
DEFAULT_DATA_FILE = "ebs-data.csv"
DEFAULT_DATA_FILE_SOURCE = "local"  # can be "local" or "s3"
DEFAULT_CROSS_ACCOUNT_ROLE_NAME = "CrossAccountObservabilityRole"


def main():
    args = parse_args()
    init_logging(args.logging)

    role_name = args.role_name
    bucket_name = args.bucket_name
    key_prefix = args.key_prefix
    data_file = args.data_file
    data_file_source = args.data_file_source
    s3_region = args.s3_region

    # Check if the data file exists
    if data_file_source == "local":
        if not os.path.exists(data_file):
            logging.error(f"Error: Account file '{data_file}' not found.")
            exit(1)
        print(f"Using account file: {data_file}")
    else:
        s3_path = (
            f"s3://{bucket_name}/{key_prefix}/{data_file}"
            if key_prefix
            else f"s3://{bucket_name}/{data_file}"
        )
        print(f"Using data file from S3: {s3_path}")

    available_regions = boto3.session.Session().get_available_regions("s3")
    if s3_region not in available_regions:
        logging.error(f"Error: The specified S3 region {s3_region} is not valid.")
        logging.error(f"Available regions are: {available_regions}")
        exit(1)

    # Initialize S3 client (you can also use assumed role credentials here)
    s3_client = boto3.client("s3", region_name=s3_region)

    # Read EBS Data
    ebs_data = read_ebs_data(
        source=data_file_source,  # This should be defined in argparse
        s3_client=s3_client,
        bucket_name=bucket_name,
        key_prefix=key_prefix,
        file_name=data_file,
    )

    # Process EBS Data
    processed_data = process_ebs_data(ebs_data)

    # Output
    for data in processed_data:
        print(data)


def init_logging(level):
    logging_level = level.upper()
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_ebs_data(
    source, s3_client=None, bucket_name=None, key_prefix=None, file_name=None
):
    content = []
    if source == "s3":
        s3_key = file_name if not key_prefix else f"{key_prefix}/{file_name}"
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        csv_reader = csv.DictReader(
            response["Body"].read().decode("utf-8").splitlines()
        )
        content = [row for row in csv_reader]
    else:
        with open(file_name, mode="r") as file:
            csv_reader = csv.DictReader(file)
            content = [row for row in csv_reader]
    return content


def process_ebs_data(ebs_data):
    processed_data = []
    for row in ebs_data:
        tag_name = row.get("Tag-Name", "")
        tag_value = row.get("Tag-Value", "")
        volume_id = row.get("Volume-ID", "")
        region = row.get("Region", "")
        account_number = row.get("Account-Number", "")

        processed_data.append(
            f"{tag_name}_{tag_value}_{volume_id}_{region}_{account_number}"
        )

    return processed_data


def initialize_aws_clients(region):
    try:
        s3 = boto3.client("s3", region_name=region)
        cloudwatch = boto3.resource("cloudwatch", region_name=region)
        logging.debug("Initilized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)  # Stop the script here

    return s3, cloudwatch


def parse_args():
    parser = argparse.ArgumentParser(
        description="CloudWatch Dashboards Cross-Account Data Gathering"
    )
    parser.add_argument(
        "--role-name",
        type=str,
        default=DEFAULT_CROSS_ACCOUNT_ROLE_NAME,
        help=f"Specify the role name. Defaults to {DEFAULT_CROSS_ACCOUNT_ROLE_NAME}.",
    )
    parser.add_argument(
        "--s3-region",
        type=str,
        default=DEFAULT_S3_REGION,  # Default region
        help=f"Specify the S3 region. Defaults to {DEFAULT_S3_REGION}.",
    )
    parser.add_argument(
        "--bucket-name",
        type=str,
        default=DEFAULT_S3_BUCKET_NAME,
        help=f"Specify the bucket name. Defaults to {DEFAULT_S3_BUCKET_NAME}.",
    )
    parser.add_argument(
        "--key-prefix",
        type=str,
        default=DEFAULT_S3_KEY_PREFIX,
        help=f"Specify the S3 key prefix. Defaults to '{DEFAULT_S3_KEY_PREFIX or 'an empty string'}'.",
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default=DEFAULT_DATA_FILE,
        help=f"Specify the output file name. Defaults to {DEFAULT_DATA_FILE}.",
    )
    parser.add_argument(
        "--data-file-source",
        type=str,
        choices=["s3", "local"],
        default=DEFAULT_DATA_FILE_SOURCE,
        help="Specify the source of the data information file. Choices are: s3, local. Defaults to {DEFAULT_DATA_FILE_SOURCE}.",
    )
    parser.add_argument(
        "--logging",
        type=str,
        choices=["info", "warning", "debug"],
        default="info",
        help="Set the logging level. Choices are: info, warning, debug. Defaults to info.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
