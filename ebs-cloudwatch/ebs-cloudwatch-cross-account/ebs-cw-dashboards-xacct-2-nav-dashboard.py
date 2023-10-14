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
    EBS_PAGINATION = 300
    CW_WIDTH_X = 8
    CW_HEIGHT_Y = 6
    CW_MAX_WIDTH = 23
    DEFAULT_REGION = "us-west-2"


def main():
    args = parse_args()
    init_logging(args.logging)
    widgets = []
    region = args.region
    cw_nav_dashboard_name = args.cw_nav_dashboard_name

    cloudwatch_client = init_clients(region=region)

    dashboard_list = get_cloudwatch_dashboards(cloudwatch=cloudwatch_client)

    dashboard_names = [
        dash["DashboardName"]
        for dash in dashboard_list["DashboardEntries"]
        if dash["DashboardName"].startswith("EBS_")
    ]

    logging.info(f"Found {len(dashboard_names)} dashboards with prefix 'EBS_'.")
    for i, dashboard_name in enumerate(dashboard_names):
        logging.info(f"Processing dashboard: {dashboard_name}")
        x = (i % 2) * 6  # Arrange widgets in columns, 2 widgets per row
        y = (i // 2) * 6  # New row every 2 widgets
        widgets.append(
            generate_text_widget(x=x, y=y, dashboard_name=dashboard_name, region=region)
        )

    main_dashboard_body = {"widgets": widgets}

    try:
        cloudwatch_client.put_dashboard(
            DashboardName=cw_nav_dashboard_name,
            DashboardBody=json.dumps(main_dashboard_body),
        )
    except ClientError as e:
        logging.error(f"Failed to update dashboard: {e}")


def generate_dashboard_url(region, dashboard_name):
    return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}"


# Function to generate text widget for each dashboard
def generate_text_widget(x, y, dashboard_name, region):
    url = generate_dashboard_url(region=region, dashboard_name=dashboard_name)
    return {
        "type": "text",
        "x": x,
        "y": y,
        "width": 6,
        "height": 6,
        "properties": {"markdown": f"[Navigate to {dashboard_name}]({url})"},
    }


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
        "--region",
        type=str,
        default=Config.DEFAULT_REGION,
        help=f"Specify the CloudWatch Dashboard region. Defaults to {Config.DEFAULT_REGION}.",
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
