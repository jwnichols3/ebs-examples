import boto3
import logging


class Config:
    EC2_ENDPOINT_URL = "https://ec2.us-west-2.api.aws"
    CLOUDWATCH_ENDPOINT_URL = "https://monitoring.us-west-2.amazonaws.com"
    SNS_ENDPOINT_URL = "https://sns.us-west-2.amazonaws.com"
    REGION = "us-west-2"


def initialize_aws_clients():
    try:
        ec2 = boto3.client(
            "ec2", region_name=Config.REGION, endpoint_url=Config.EC2_ENDPOINT_URL
        )
        cloudwatch = boto3.client(
            "cloudwatch",
            region_name=Config.REGION,
            endpoint_url=Config.CLOUDWATCH_ENDPOINT_URL,
        )
        sns = boto3.client(
            "sns", region_name=Config.REGION, endpoint_url=Config.SNS_ENDPOINT_URL
        )
        logging.info("Initialized AWS Client in region {}".format(Config.REGION))
    except Exception as e:
        logging.error("Failed to initialize AWS clients: {}".format(e))
        exit(1)

    return ec2, cloudwatch, sns


def test_ec2_access(ec2):
    try:
        # Test by describing regions
        regions = ec2.describe_regions()
        logging.info(
            "EC2 access test successful. Regions: {}".format(regions["Regions"])
        )
    except Exception as e:
        logging.error("Failed EC2 access test: {}".format(e))


def test_cloudwatch_access(cloudwatch):
    try:
        # Test by listing dashboards
        dashboards = cloudwatch.list_dashboards()
        logging.info(
            "CloudWatch access test successful. Dashboards: {}".format(
                dashboards["DashboardEntries"]
            )
        )
    except Exception as e:
        logging.error("Failed CloudWatch access test: {}".format(e))


def test_sns_access(sns):
    try:
        # Test by listing topics
        topics = sns.list_topics()
        logging.info("SNS access test successful. Topics: {}".format(topics["Topics"]))
    except Exception as e:
        logging.error("Failed SNS access test: {}".format(e))


def main():
    logging.basicConfig(level=logging.INFO)
    ec2, cloudwatch, sns = initialize_aws_clients()
    test_ec2_access(ec2)
    test_cloudwatch_access(cloudwatch)
    test_sns_access(sns)


if __name__ == "__main__":
    main()
