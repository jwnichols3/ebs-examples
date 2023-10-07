import boto3
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


def write_to_csv(volumes, account, region, account_description):
    # Open CSV in append mode ('a')
    with open("ebs-volume-info.csv", "a", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for volume in volumes:
            # Print the data
            print(
                f"Account: {account}, Description: {account_description}, Region: {region}, Volume ID: {volume['VolumeId']}, Status: {volume['State']}, Size: {volume['Size']}GB, Type: {volume['VolumeType']}"
            )
            # Write the data to CSV
            csvwriter.writerow(
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


if __name__ == "__main__":
    role_name = "CrossAccountObservabilityRole"

    # Write header to the CSV file and open it in write mode ('w')
    with open("ebs-volume-info.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(
            [
                "Account-Number",
                "Account-Description",
                "Region",
                "Volume ID",
                "Volume Status",
                "Volume Size",
                "Volume Type",
            ]
        )

    # Read account info from CSV
    with open("account-information.csv", "r") as csvfile:
        csvreader = csv.reader(csvfile)
        header = next(csvreader)  # Skip the header row
        for row in csvreader:
            account, region, account_description = row

            # Assume role and get temporary credentials
            temp_credentials = assume_role(account, role_name)

            # List EBS volumes using the temporary credentials
            ebs_volumes = list_ebs_volumes(temp_credentials, region)

            # Write volumes to CSV and print the data
            write_to_csv(
                volumes=ebs_volumes["Volumes"],
                account=account,
                region=region,
                account_description=account_description,
            )
