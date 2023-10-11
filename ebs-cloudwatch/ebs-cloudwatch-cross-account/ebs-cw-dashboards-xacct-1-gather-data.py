import boto3
import csv
import tempfile
import shutil
import argparse
import os
import logging

EBS_PAGINATION = 300


def main():
    args = parse_args()
    init_logging(args.logging)

    account_file = args.account_file
    role_name = args.role_name
    bucket_name = args.bucket_name
    key_prefix = args.key_prefix
    data_file = args.data_file  # This will be used for both S3 and local file

    # Check if the account file exists
    if not os.path.exists(account_file):
        logging.error(f"Error: Account file '{account_file}' not found.")
        exit(1)

    print(f"Using account file: {account_file}")

    available_regions = boto3.session.Session().get_available_regions("s3")
    if args.s3_region not in available_regions:
        logging.error(f"Error: The specified S3 region {args.s3_region} is not valid.")
        logging.error(f"Available regions are: {available_regions}")
        exit(1)

    # Initialize S3 client (you can also use assumed role credentials here)
    s3_client = boto3.client("s3", region_name=args.s3_region)

    try:
        # Create a single temp file to hold all data
        with tempfile.NamedTemporaryFile(
            mode="w+", newline="", delete=False
        ) as main_tmpfile:
            main_csvwriter = csv.writer(main_tmpfile)
            # Write header
            main_csvwriter.writerow(
                [
                    "Account-Number",
                    "Account-Description",
                    "Region",
                    "Volume-ID",
                    "Volume-Status",
                    "Volume-Size",
                    "Volume-Type",
                    "Tag-Name",
                    "Tag-Value",
                ]
            )

            # Read account info from CSV
            with open(account_file, "r") as csvfile:
                csvreader = csv.DictReader(csvfile)
                logging.info(f"CSV Headers: {csvreader.fieldnames}")
                for row in csvreader:
                    account = row.get("account-number")
                    region = row.get("region")
                    account_description = row.get("account-description")
                    tag_name = row.get("tag-name")
                    handle_account_processing(
                        account=account,
                        region=region,
                        account_description=account_description,
                        main_csvwriter=main_csvwriter,
                        role_name=role_name,
                        tag_name=tag_name,
                    )

            main_tmpfile.flush()

            shutil.copy(main_tmpfile.name, data_file)

            # Determine S3 key
            s3_key = data_file if not key_prefix else f"{key_prefix}/{data_file}"

            try:
                s3_client.upload_file(main_tmpfile.name, bucket_name, s3_key)
                logging.info(f"Successfully uploaded to {bucket_name}/{s3_key}")
            except Exception as e:
                logging.error(f"Error uploading to S3: {e}")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    # Read and print the S3 file
    read_and_print_s3_file(s3_client, bucket_name, s3_key)


def handle_account_processing(
    account, region, account_description, main_csvwriter, role_name, tag_name
):
    try:
        temp_credentials = assume_role(account, role_name)
    except Exception as e:
        logging.error(
            f"Error assuming role for account {account} ({account_description}): {e}"
        )
        return

    logging.info(f"Assumed role for account: {account} ({account_description})")

    try:
        ebs_volumes = list_ebs_volumes(
            credentials=temp_credentials, region=region, tag_name=tag_name
        )
    except Exception as e:
        logging.error(f"Error listing EBS volumes for account {account}: {e}")
        return

    if not ebs_volumes.get("Volumes"):
        logging.info(
            f"No EBS volumes found for account {account} ({account_description})."
        )
        return

    volume_count = len(ebs_volumes["Volumes"])
    logging.info(
        f"Retrieved {volume_count} EBS volumes for account: {account} ({account_description})"
    )

    for volume in ebs_volumes["Volumes"]:
        tag_value = next(
            (tag["Value"] for tag in volume.get("Tags", []) if tag["Key"] == tag_name),
            "N/A",
        )
        main_csvwriter.writerow(
            [
                account,
                account_description,
                region,
                volume["VolumeId"],
                volume["State"],
                volume["Size"],
                volume["VolumeType"],
                tag_name,
                tag_value,
            ]
        )


def assume_role(account_id, role_name):
    sts_client = boto3.client("sts")
    assumed_role_object = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="AssumeRoleSession",
    )
    credentials = assumed_role_object["Credentials"]
    return credentials


def list_ebs_volumes(credentials, region, tag_name):
    ec2_client = boto3.client(
        "ec2",
        region_name=region,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    all_volumes = []
    next_token = None

    while True:
        if next_token:
            response = ec2_client.describe_volumes(
                MaxResults=EBS_PAGINATION,
                NextToken=next_token,
                Filters=[{"Name": f"tag:{tag_name}", "Values": ["*"]}],
            )
        else:
            response = ec2_client.describe_volumes(
                MaxResults=EBS_PAGINATION,
                Filters=[{"Name": f"tag:{tag_name}", "Values": ["*"]}],
            )

        all_volumes.extend(response.get("Volumes", []))

        next_token = response.get("NextToken")
        if not next_token:
            break

    return {"Volumes": all_volumes}


def read_and_print_s3_file(s3_client, bucket_name, s3_key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = response["Body"].read().decode("utf-8")
        logging.info("Contents of S3 File:\n")
        logging.info(file_content)
    except Exception as e:
        logging.error(f"An error occurred while reading S3 file: {e}")


def init_logging(level):
    logging_level = level.upper()
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="CloudWatch Dashboards Cross-Account Data Gathering"
    )
    parser.add_argument(
        "--account-file",
        type=str,
        default="account-info.csv",
        help="Specify the account information file. Defaults to account-info.csv.",
    )
    parser.add_argument(
        "--role-name",
        type=str,
        default="CrossAccountObservabilityRole",
        help="Specify the role name. Defaults to CrossAccountObservabilityRole.",
    )
    parser.add_argument(
        "--s3-region",
        type=str,
        default="us-west-2",  # Default region
        help="Specify the S3 region. Defaults to us-west-2.",
    )
    parser.add_argument(
        "--bucket-name",
        type=str,
        default="jnicmazn-ebs-observability-us-west-2",
        help="Specify the bucket name. Defaults to jnicmazn-ebs-observability-us-west-2.",
    )
    parser.add_argument(
        "--key-prefix",
        type=str,
        default="",
        help="Specify the S3 key prefix. Defaults to empty string.",
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="ebs-volume-info.csv",
        help="Specify the output file name. Defaults to ebs-volume-info.csv.",
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
