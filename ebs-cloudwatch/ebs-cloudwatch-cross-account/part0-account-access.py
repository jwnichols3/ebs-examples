import boto3
import json
import csv


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


if __name__ == "__main__":
    role_name = "CrossAccountObservabilityRole"

    # Read account info from CSV
    with open("account-information.csv", "r") as csvfile:
        csvreader = csv.reader(csvfile)
        header = next(csvreader)  # Skip the header row
        for row in csvreader:
            account, region, account_description = row
            print(
                f"Listing EBS Volumes for Account {account} ({account_description}) in Region {region}"
            )

            # Assume role and get temporary credentials
            temp_credentials = assume_role(account, role_name)

            # List EBS volumes using the temporary credentials
            ebs_volumes = list_ebs_volumes(temp_credentials, region)

            for volume in ebs_volumes["Volumes"]:
                print(
                    f"  Volume ID: {volume['VolumeId']}, Size: {volume['Size']}GB, State: {volume['State']}"
                )
