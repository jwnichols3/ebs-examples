import boto3
import csv
import tempfile
import shutil
import argparse
import os


def main():
    args = parse_args()

    account_file = args.account_file
    role_name = args.role_name
    bucket_name = args.bucket_name
    key_prefix = args.key_prefix
    output_file = args.output_file  # This will be used for both S3 and local file

    # Check if the account file exists
    if not os.path.exists(account_file):
        print(f"Error: Account file '{account_file}' not found.")
        exit(1)

    print(f"Using account file: {account_file}")

    available_regions = boto3.session.Session().get_available_regions("s3")
    if args.s3_region not in available_regions:
        print(f"Error: The specified S3 region {args.s3_region} is not valid.")
        print(f"Available regions are: {available_regions}")
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
                ]
            )

            # Read account info from CSV
            with open(account_file, "r") as csvfile:
                csvreader = csv.DictReader(csvfile)
                print(f"CSV Headers: {csvreader.fieldnames}")
                for row in csvreader:
                    account = row.get("account-number")
                    region = row.get("region")
                    account_description = row.get("account-description")
                    handle_account_processing(
                        account, region, account_description, main_csvwriter, role_name
                    )

            main_tmpfile.flush()

            shutil.copy(main_tmpfile.name, output_file)

            # Determine S3 key
            s3_key = output_file if not key_prefix else f"{key_prefix}/{output_file}"

            try:
                s3_client.upload_file(main_tmpfile.name, bucket_name, s3_key)
                print(f"Successfully uploaded to {bucket_name}/{s3_key}")
            except Exception as e:
                print(f"Error uploading to S3: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Read and print the S3 file
    read_and_print_s3_file(s3_client, bucket_name, s3_key)


def handle_account_processing(
    account, region, account_description, main_csvwriter, role_name
):
    try:
        temp_credentials = assume_role(account, role_name)
    except Exception as e:
        print(f"Error assuming role for account {account} ({account_description}): {e}")
        return

    print(f"Assumed role for account: {account} ({account_description})")

    try:
        ebs_volumes = list_ebs_volumes(temp_credentials, region)
    except Exception as e:
        print(f"Error listing EBS volumes for account {account}: {e}")
        return

    if not ebs_volumes.get("Volumes"):
        print(f"No EBS volumes found for account {account} ({account_description}).")
        return

    volume_count = len(ebs_volumes["Volumes"])
    print(
        f"Retrieved {volume_count} EBS volumes for account: {account} ({account_description})"
    )

    for volume in ebs_volumes["Volumes"]:
        main_csvwriter.writerow(
            [
                account,
                account_description,
                region,
                volume["VolumeId"],
                volume["State"],
                volume["Size"],
                volume["VolumeType"],
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


def list_ebs_volumes(credentials, region):
    ec2_client = boto3.client(
        "ec2",
        region_name=region,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    volumes = ec2_client.describe_volumes()
    return volumes


def read_and_print_s3_file(s3_client, bucket_name, s3_key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = response["Body"].read().decode("utf-8")
        print("Contents of S3 File:")
        print(file_content)
    except Exception as e:
        print(f"An error occurred while reading S3 file: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="AWS EBS Information")
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
        "--output-file",
        type=str,
        default="ebs-volume-info.csv",
        help="Specify the output file name. Defaults to ebs-volume-info.csv.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
