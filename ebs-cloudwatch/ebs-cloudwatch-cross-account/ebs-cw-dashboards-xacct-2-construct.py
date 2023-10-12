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
DEFAULT_ACCOUNT_INFO_FILE = "account-info.csv"
DEFAULT_ACCOUNT_FILE_SOURCE = "local"  # can be "local" or "s3"
DEFAULT_CROSS_ACCOUNT_ROLE_NAME = "CrossAccountObservabilityRole"


def main():
    args = parse_args()
    init_logging(args.logging)

    account_file = args.account_file
    role_name = args.role_name
    bucket_name = args.bucket_name
    key_prefix = args.key_prefix
    data_file = args.data_file

    # Check if the account file exists
    if args.account_file_source == "local":
        if not os.path.exists(account_file):
            logging.error(f"Error: Account file '{account_file}' not found.")
            exit(1)
        print(f"Using account file: {account_file}")
    else:
        s3_path = (
            f"s3://{bucket_name}/{key_prefix}/{account_file}"
            if key_prefix
            else f"s3://{bucket_name}/{account_file}"
        )
        print(f"Using account file from S3: {s3_path}")

    available_regions = boto3.session.Session().get_available_regions("s3")
    if args.s3_region not in available_regions:
        logging.error(f"Error: The specified S3 region {args.s3_region} is not valid.")
        logging.error(f"Available regions are: {available_regions}")
        exit(1)

    # Initialize S3 client (you can also use assumed role credentials here)
    s3_client = boto3.client("s3", region_name=args.s3_region)

    account_file_lines = read_account_file(
        args.account_file_source,
        s3_client,
        args.bucket_name,
        args.key_prefix,
        args.account_file,
    )


def init_logging(level):
    logging_level = level.upper()
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_account_file(
    source, s3_client=None, bucket_name=None, key_prefix=None, local_path=None
):
    if source == "s3":
        s3_key = local_path if not key_prefix else f"{key_prefix}/{local_path}"
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = response["Body"].read().decode("utf-8")
        return content.splitlines()
    else:
        with open(local_path, "r") as f:
            return f.readlines()


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
        "--account-file",
        type=str,
        default=DEFAULT_ACCOUNT_INFO_FILE,
        help=f"Specify the account information file. Defaults to {DEFAULT_ACCOUNT_INFO_FILE}.",
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
        "--account-file-source",
        type=str,
        choices=["s3", "local"],
        default=DEFAULT_ACCOUNT_FILE_SOURCE,
        help="Specify the source of the account information file. Choices are: s3, local. Defaults to {DEFAULT_ACCOUNT_FILE_SOURCE}.",
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
