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
    EBS_PAGINATION = 300
    CW_WIDGET_X = 8  # The width of the widgets on the constructed pages.
    CW_WIDGET_Y = 6  # The height of the widgets on constructed pages.
    CW_WIDGET_MAX_WIDTH = 23  # Width boundaries or used for full-width widgets
    CW_WIDGET_MAX_HEIGHT = 999  # A widget's maximum height.
    CW_WIDGET_METRICS_LIMIT = 500
    CW_DASHBOARD_METRICS_LIMIT = 2500
    CW_DASHBOARD_NAME_PREFIX = "EBS_"
    CW_MAINNAV_NAME = "0_" + CW_DASHBOARD_NAME_PREFIX + "_NAV"
    CW_MAINNAV_WIDGET_HEIGHT_BUFFER = 4
    DEFAULT_CW_REGION = "us-west-2"
    DEFAULT_S3_REGION = "us-west-2"
    DEFAULT_S3_BUCKET_NAME = "jnicmazn-ebs-observability-us-west-2"
    DEFAULT_S3_KEY_PREFIX = ""
    DEFAULT_CONSTRUCTION_DATA_FILE = "ebs-data.csv"
    DEFAULT_CONSTRUCTION_DATA_FILE_SOURCE = "local"
    DEFAULT_CROSS_ACCOUNT_ROLE_NAME = "CrossAccountObservabilityRole"


def main():
    args = parse_args()
    init_logging(args.logging)

    validate_file_exists(args=args)
    validate_region(args=args)

    s3_client, cloudwatch_client = init_clients(
        s3_region=args.s3_region, cw_region=args.cw_region
    )
    construction_data = read_construction_data(args=args, s3_client=s3_client)
    processed_data = process_construction_data(construction_data=construction_data)

    created_dashboards = create_dashboards(
        cloudwatch_client=cloudwatch_client, processed_data=processed_data
    )

    logging.debug(
        f"Created dashboards going into create_main_nav_dashboard\n{created_dashboards}\n"
    )
    create_main_nav_dashboard(
        cloudwatch_client=cloudwatch_client,
        processed_data=processed_data,
        dashboard_names=created_dashboards,
    )


def read_construction_data(args, s3_client):
    source = args.data_file_source
    bucket = args.bucket_name
    key_prefix = args.key_prefix
    file_name = args.data_file

    s3_key = f"{key_prefix}/{file_name}" if key_prefix else file_name

    return (
        read_csv_from_s3(s3_client, bucket, s3_key)
        if source == "s3"
        else read_csv_from_local(file_name)
    )


def process_construction_data(construction_data):
    structured_data = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    )

    for row in construction_data:  # construction_data is now a list of dictionaries
        tag_name, tag_value, volume_id, region, account = (
            row.get("Tag-Name", ""),
            row.get("Tag-Value", ""),
            row.get("Volume-ID", ""),
            row.get("Region", ""),
            row.get("Account-Number", ""),
        )
        dashboard_name = f"{tag_name}_{tag_value}_{region}_{account}"
        graph_content = {
            "Graph Name": f"{volume_id}_{region}",
            "Metric 1": "manually_constructed_metric_1",
            "Metric 2": "manually_constructed_metric_2",
        }
        target = structured_data[tag_name][tag_value][region][account]
        target["dashboard_name"] = dashboard_name
        target.setdefault("graph_contents", []).append(graph_content)

    return structured_data


def create_dashboards(cloudwatch_client, processed_data):
    created_dashboards = []
    for tag_name, tag_values in processed_data.items():
        for tag_value, regions in tag_values.items():
            for region, account_numbers in regions.items():
                for account_number, details in account_numbers.items():
                    base_dashboard_name = Config.CW_DASHBOARD_NAME_PREFIX + details.get(
                        "dashboard_name", ""
                    )

                    shard_suffix = 1
                    dashboard_name = f"{base_dashboard_name}_{shard_suffix}"
                    graph_contents = details.get("graph_contents", [])

                    metric_count = 0  # Initialize metric count for each new dashboard
                    widgets = [create_top_nav_widget()]

                    for graph_content in graph_contents:
                        widget, widget_metric_count = create_widget(
                            dashboard_name, graph_content, account_number, region
                        )
                        metric_count += widget_metric_count  # Update the metric count

                        # Check if the dashboard has exceeded the metric limit
                        if metric_count > Config.CW_DASHBOARD_METRICS_LIMIT:
                            put_dashboard(
                                cloudwatch_client=cloudwatch_client,
                                dashboard_name=dashboard_name,
                                widgets=widgets,
                            )  # Save the current dashboard
                            created_dashboards.append(dashboard_name)

                            # Prepare for the next shard
                            shard_suffix += 1
                            dashboard_name = f"{base_dashboard_name}_{shard_suffix}"
                            metric_count = widget_metric_count  # Reset metric count
                            widgets = [create_top_nav_widget()]
                            widgets.append(widget)

                        else:
                            widgets.append(
                                widget
                            )  # Add widget to the current dashboard

                    # Create the last dashboard if there are any remaining widgets
                    if widgets:
                        put_dashboard(
                            cloudwatch_client=cloudwatch_client,
                            dashboard_name=dashboard_name,
                            widgets=widgets,
                        )
                        created_dashboards.append(dashboard_name)

    return created_dashboards


def create_top_nav_widget():
    main_nav_link = f"#dashboards:name={Config.CW_MAINNAV_NAME}"
    return {
        "type": "text",
        "width": Config.CW_WIDGET_MAX_WIDTH,
        "height": 2,  # You can adjust the height as needed
        "properties": {"markdown": f"[Go to Main Navigation]({main_nav_link})"},
    }


def put_dashboard(cloudwatch_client, dashboard_name, widgets):
    dashboard_body = {"widgets": widgets}
    try:
        cloudwatch_client.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body),
        )
        logging.info(f"Successfully created/updated dashboard: {dashboard_name}.")
    except ClientError as e:
        logging.error(
            f"Failed to create/update dashboard: {dashboard_name}. Error: {e}"
        )


def create_widget(dashboard_name, graph_content, account_number, region):
    volume_id = graph_content["Graph Name"].split("_")[0]
    widget = {
        "type": "metric",
        "width": Config.CW_WIDGET_X,
        "height": Config.CW_WIDGET_Y,
        "properties": {
            "view": "timeSeries",
            "stacked": False,
            "metrics": [
                [
                    "AWS/EBS",
                    "VolumeTotalWriteTime",
                    "VolumeId",
                    volume_id,
                    {
                        "region": region,
                        "accountId": account_number,
                        "id": "m1",
                        "label": f"{volume_id}_VolumeTotalWriteTime",
                        "visible": False,
                        "color": "#69ae34",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeWriteOps",
                    "VolumeId",
                    volume_id,
                    {
                        "region": region,
                        "accountId": account_number,
                        "id": "m2",
                        "label": f"{volume_id}_VolumeWriteOps",
                        "visible": False,
                        "color": "#69ae34",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeQueueLength",
                    "VolumeId",
                    volume_id,
                    {
                        "region": region,
                        "accountId": account_number,
                        "id": "m3",
                        "label": f"{volume_id}_VolumeQueueLength",
                        "visible": True,
                        "yAxis": "right",
                        "color": "#08aad2",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeTotalReadTime",
                    "VolumeId",
                    volume_id,
                    {
                        "region": region,
                        "accountId": account_number,
                        "id": "m4",
                        "label": f"{volume_id}_VolumeTotalReadTime",
                        "visible": False,
                        "color": "#dfb52c",
                    },
                ],
                [
                    "AWS/EBS",
                    "VolumeReadOps",
                    "VolumeId",
                    volume_id,
                    {
                        "region": region,
                        "accountId": account_number,
                        "id": "m5",
                        "label": f"{volume_id}_VolumeReadOps",
                        "visible": False,
                        "color": "#dfb52c",
                    },
                ],
                [
                    {
                        "expression": "(m1 / m2) * 1000",
                        "label": f"{volume_id}_WriteLatency",
                        "id": "e1",
                        "region": region,
                        "accountId": account_number,
                        "visible": True,
                        "yAxis": "left",
                        "color": "#69ae34",
                    }
                ],
                [
                    {
                        "expression": "(m4 / m5) * 1000",
                        "label": f"{volume_id}_ReadLatency",
                        "id": "e2",
                        "region": region,
                        "accountId": account_number,
                        "visible": True,
                        "yAxis": "left",
                        "color": "#dfb52c",
                    }
                ],
                [
                    {
                        "expression": "IF(m3>0 AND m2+m5==0, 1, 0)",
                        "label": f"{volume_id}_ImpairedVol",
                        "id": "e3",
                        "region": region,
                        "accountId": account_number,
                        "visible": True,
                        "yAxis": "left",
                        "color": "#fe6e73",
                    }
                ],
            ],
            "region": region,  # Added based on your example
            "period": 300,  # Added based on your example
            "title": f"{dashboard_name} - {volume_id}",
        },
    }

    widget_metric_count = len(widget["properties"]["metrics"])
    return widget, widget_metric_count  # Return the widget and its metric count


def create_main_nav_dashboard(cloudwatch_client, processed_data, dashboard_names):
    # Count the number of dashboards and add a buffer to set the height
    dashboard_count = len(dashboard_names)
    dynamic_height = dashboard_count + Config.CW_MAINNAV_WIDGET_HEIGHT_BUFFER

    main_dashboard_body = {
        "widgets": [
            generate_main_nav_widget(
                dashboard_names=dashboard_names, dynamic_height=dynamic_height
            )
        ]
    }

    try:
        cloudwatch_client.put_dashboard(
            DashboardName=Config.CW_MAINNAV_NAME,
            DashboardBody=json.dumps(main_dashboard_body),
        )
        logging.info(f"Successfully created/updated navigation dashboard.")
    except ClientError as e:
        logging.error(f"Failed to create/update navigation dashboard. Error: {e}")


def generate_main_nav_widget(dashboard_names, dynamic_height):
    # Initialize Markdown content with table header
    markdown_content = "## Dashboards Navigation\n\n| Dashboard Link |\n| ---- |\n"

    # Add table rows for each dashboard
    for dashboard_name in dashboard_names:
        dashboard_url = f"#dashboards:name={dashboard_name}"
        markdown_content += f"| [Go to {dashboard_name}]({dashboard_url}) |\n"

    dashboard_content = {
        "type": "text",
        "width": Config.CW_WIDGET_MAX_WIDTH,
        "height": dynamic_height,  # Set height dynamically
        "properties": {"markdown": markdown_content},
    }

    logging.debug(f"Generated dashboard content: {json.dumps(dashboard_content)}")

    return dashboard_content


def init_clients(s3_region, cw_region):
    s3_client = boto3.client("s3", region_name=s3_region)
    cloudwatch_client = boto3.client("cloudwatch", region_name=cw_region)
    return s3_client, cloudwatch_client


def init_logging(level):
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_csv_from_s3(s3_client, bucket, key):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return csv.DictReader(response["Body"].read().decode("utf-8").splitlines())
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logging.error(f"Error: Object '{key}' not found in bucket '{bucket}'.")
        elif e.response["Error"]["Code"] == "AccessDenied":
            logging.error(
                f"Error: Access denied to object '{key}' in bucket '{bucket}'."
            )
        else:
            logging.error(f"An unexpected error occurred: {e}")
        exit(1)


def read_csv_from_local(file_path):
    with open(file_path, "r") as f:
        return list(csv.DictReader(f))


def validate_region(args):
    s3_region = args.s3_region
    available_regions = boto3.session.Session().get_available_regions("s3")

    if s3_region not in available_regions:
        logging.error(f"Error: The specified S3 region {s3_region} is not valid.")
        exit(1)


def validate_file_exists(args):
    data_file_source = args.data_file_source
    data_file = args.data_file

    if data_file_source == "local" and not os.path.exists(data_file):
        logging.error(f"Error: Account file '{data_file}' not found.")
        exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="CloudWatch Dashboards Cross-Account Data Gathering"
    )
    parser.add_argument(
        "--role-name",
        type=str,
        default=Config.DEFAULT_CROSS_ACCOUNT_ROLE_NAME,
        help=f"Specify the role name. Defaults to {Config.DEFAULT_CROSS_ACCOUNT_ROLE_NAME}.",
    )
    parser.add_argument(
        "--cw-region",
        type=str,
        default=Config.DEFAULT_CW_REGION,
        help=f"Specify the CloudWatch Dashboard region. Defaults to {Config.DEFAULT_CW_REGION}.",
    )
    parser.add_argument(
        "--s3-region",
        type=str,
        default=Config.DEFAULT_S3_REGION,
        help=f"Specify the S3 region. Defaults to {Config.DEFAULT_S3_REGION}.",
    )
    parser.add_argument(
        "--bucket-name",
        type=str,
        default=Config.DEFAULT_S3_BUCKET_NAME,
        help=f"Specify the bucket name. Defaults to {Config.DEFAULT_S3_BUCKET_NAME}.",
    )
    parser.add_argument(
        "--key-prefix",
        type=str,
        default=Config.DEFAULT_S3_KEY_PREFIX,
        help=f"Specify the S3 key prefix. Defaults to {Config.DEFAULT_S3_KEY_PREFIX if Config.DEFAULT_S3_KEY_PREFIX else 'an empty string'}.",
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default=Config.DEFAULT_CONSTRUCTION_DATA_FILE,
        help=f"Specify the output file name. Defaults to {Config.DEFAULT_CONSTRUCTION_DATA_FILE}.",
    )
    parser.add_argument(
        "--data-file-source",
        type=str,
        choices=["s3", "local"],
        default=Config.DEFAULT_CONSTRUCTION_DATA_FILE_SOURCE,
        help=f"Specify the source of the data information file. Choices are: s3, local. Defaults to {Config.DEFAULT_CONSTRUCTION_DATA_FILE_SOURCE}.",
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
