import boto3
import logging


class Config:
    DEFAULT_REGION = "us-west-2"
    EC2_ENDPOINT_URL = f"https://ec2.{DEFAULT_REGION}.api.aws"  # this is the dual-stack endpoint (IPv4 and IPv6)
    CLOUDWATCH_ENDPOINT_URL = f"https://monitoring.{DEFAULT_REGION}.amazonaws.com"
    SNS_ENDPOINT_URL = f"https://sns.{DEFAULT_REGION}.amazonaws.com"


def initialize_aws_clients():
    try:
        ec2 = boto3.client(
            "ec2",
            region_name=Config.DEFAULT_REGION,
            endpoint_url=Config.EC2_ENDPOINT_URL,
        )
        cloudwatch = boto3.client(
            "cloudwatch",
            region_name=Config.DEFAULT_REGION,
            endpoint_url=Config.CLOUDWATCH_ENDPOINT_URL,
        )
        sns = boto3.client(
            "sns",
            region_name=Config.DEFAULT_REGION,
            endpoint_url=Config.SNS_ENDPOINT_URL,
        )
        logging.info(
            "Initialized AWS Client in region {}".format(Config.DEFAULT_REGION)
        )
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


def can_connect_to_endpoint(endpoint_url):
    """Check if the script can connect to the given endpoint URL."""
    import requests

    try:
        response = requests.get(endpoint_url, timeout=5)
        print(f"request response: \n{response}")
        return True if response.status_code == 200 else False
    except requests.RequestException:
        return False


def get_and_print_vpc_endpoints_dns_entries(ec2):
    if not can_connect_to_endpoint(Config.EC2_ENDPOINT_URL):
        logging.warning(
            "Cannot connect to EC2 VPC Endpoint. Ensure you're running this within the VPC or have necessary connectivity setup."
        )
        return

    try:
        vpc_endpoints = ec2.describe_vpc_endpoints()
        for endpoint in vpc_endpoints.get("VpcEndpoints", []):
            print(f"VPC Endpoint ID: {endpoint['VpcEndpointId']}")
            for entry in endpoint.get("DnsEntries", []):
                print(f"\tDNS name: {entry['DnsName']}")
                print(f"\tDNS IP: {entry['DnsIpAddresses']}")
    except Exception as e:
        logging.error("Failed to get VPC Endpoints DNS entries: {}".format(e))


def main():
    logging.basicConfig(level=logging.INFO)
    ec2, cloudwatch, sns = initialize_aws_clients()
    test_ec2_access(ec2)
    test_cloudwatch_access(cloudwatch)
    test_sns_access(sns)
    get_and_print_vpc_endpoints_dns_entries(ec2)


if __name__ == "__main__":
    main()
