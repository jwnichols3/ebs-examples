import boto3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# List of AWS account IDs you want to access
accounts = [
    "627710063647",
    "338557412966",
    "357044226454",
]  # Replace these with your actual account IDs

# The SSO profile name
sso_profile_name = "jnicamzn-sso-root-admin"


def list_ebs_volumes(account_id, sso_profile):
    """
    Lists EBS volumes for a given account using a specific SSO profile.
    """
    try:
        # Create a session using the specified SSO profile
        session = boto3.Session(profile_name=sso_profile)

        # Create an EC2 client from the session
        ec2_client = session.client("ec2")

        # Call the AWS EC2 API to list volumes
        volumes = ec2_client.describe_volumes()

        logging.info(
            f"Account {account_id}: Found {len(volumes['Volumes'])} EBS volumes"
        )
        for volume in volumes["Volumes"]:
            logging.info(
                f"Volume ID: {volume['VolumeId']}, Size: {volume['Size']} GiB, State: {volume['State']}"
            )

    except Exception as e:
        logging.error(f"An error occurred: {e}")


def main():
    """
    Main function to cycle through accounts and list EBS volumes.
    """
    for account_id in accounts:
        logging.info(f"Accessing account {account_id}")
        list_ebs_volumes(account_id, sso_profile_name)


if __name__ == "__main__":
    main()
