import boto3
import csv
import json
import argparse
import os
import logging
from botocore.exceptions import ClientError
from collections import defaultdict


# Use this class to set the Defaults and Constants. The variable format is Config.CONSTANT_NAME
class Config:
    DEFAULT_CW_NAV_DASHBOARD_NAME = "0_EBS_NAV"
    CW_DASHBOARD_NAME_PREFIX = "EBS_"
    CW_FULL_WIDTH = 24
    DEFAULT_CW_REGION = "us-west-2"


def main():
    args = parse_args()
    init_logging(args.logging)
    region = args.cw_region
    cw_nav_dashboard_name = args.cw_nav_dashboard_name

    cloudwatch_client = init_clients(region=region)

    dashboard_list = get_cloudwatch_dashboards(cloudwatch=cloudwatch_client)

    dashboard_names = [
        dash["DashboardName"]
        for dash in dashboard_list["DashboardEntries"]
        if dash["DashboardName"].startswith("EBS_")
    ]

    main_dashboard_body = {
        "widgets": [generate_single_text_widget(dashboard_names=dashboard_names)]
    }

    try:
        cloudwatch_client.put_dashboard(
            DashboardName=cw_nav_dashboard_name,
            DashboardBody=json.dumps(main_dashboard_body),
        )
    except ClientError as e:
        logging.error(f"Failed to update dashboard: {e}")


def generate_single_text_widget(dashboard_names):
    # Initialize Markdown content with table header
    markdown_content = "## Dashboards Navigation\n\n| Dashboard Link |\n| ---- |\n"

    # Add table rows for each dashboard
    for dashboard_name in dashboard_names:
        dashboard_url = f"#dashboards:name={dashboard_name}"

        logging.info(f"Markdowndown {dashboard_url}")
        markdown_content += f"| [Go to {dashboard_name}]({dashboard_url}) |\n"

    dashboard_content = {
        "type": "text",
        "width": Config.CW_FULL_WIDTH,
        "properties": {"markdown": markdown_content},
    }

    logging.debug(f"Generated dashboard content: {json.dumps(dashboard_content)}")

    return dashboard_content


def get_cloudwatch_dashboards(cloudwatch):
    try:
        dashboards = cloudwatch.list_dashboards(
            DashboardNamePrefix=Config.CW_DASHBOARD_NAME_PREFIX
        )
    except ClientError as e:
        logging.error(f"Failed to update dashboard: {e}")

    return dashboards


def init_clients(region):
    cloudwatch = boto3.client("cloudwatch", region_name=region)

    return cloudwatch


def init_logging(level):
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create/Update CloudWatch Navigation Dashboards for Cross-Account Cross-Region EBS Metrics"
    )
    parser.add_argument(
        "--cw-region",
        type=str,
        default=Config.DEFAULT_CW_REGION,
        help=f"Specify the CloudWatch Dashboard region. Defaults to {Config.DEFAULT_CW_REGION}.",
    )
    parser.add_argument(
        "--cw-nav-dashboard-name",
        type=str,
        default=Config.DEFAULT_CW_NAV_DASHBOARD_NAME,
        help=f"Specify the name of the CloudWatch Navigation Dashboard. Defaults to {Config.DEFAULT_CW_NAV_DASHBOARD_NAME}.",
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
