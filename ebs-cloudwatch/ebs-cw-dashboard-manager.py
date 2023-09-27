import boto3
import argparse
import logging
import json
import sys
import collections

# Constants
DASHBOARD_METRIC_LIMIT = 2500
GRAPH_METRIC_LIMIT = 500
GRAPH_DEFAULT_WIDTH = 12
GRAPH_DEFAULT_HEIGHT = 5


def main():
    try:
        ec2_region = boto3.client("ec2")  # Initialize EC2 client to get valid regions
        valid_regions = get_valid_aws_regions(ec2_client=ec2_region)
    except Exception as e:
        logging.error("Error initializing EC2 client: %s", e)
        sys.exit(1)

    args = parse_args(regions=valid_regions)

    initialize_logging(args.loglevel)

    if args.list_regions:
        logging.info("Valid AWS regions:\n{}".format("\n".join(valid_regions)))
        sys.exit(0)

    ec2_client, cloudwatch = initialize_aws_clients(region=args.region)

    if args.list_tags or args.list_tag_names:
        ec2_client = initialize_aws_clients(region=args.region)[0]
        ebs_volumes = get_ebs_volumes(ec2_client=ec2_client)
        tag_data = get_tag_data(ebs_volumes=ebs_volumes)

        if args.list_tags:
            list_unique_tags(tag_data=tag_data)
        if args.list_tag_names:
            list_unique_tag_names(tag_data=tag_data)

        sys.exit(0)

    ebs_volumes = get_ebs_volumes(ec2_client=ec2_client)
    all_tag_names = set(get_tag_data(ebs_volumes=ebs_volumes).keys())

    tag_keys = get_tag_keys_from_args(args)

    # Check if provided tag_keys exist
    for tag_key in tag_keys:
        if tag_key not in all_tag_names:
            logging.error(f"Tag key {tag_key} does not exist. Exiting.")
            sys.exit(1)

    # Group volumes by tag combinations
    tag_combinations = {}
    for volume in ebs_volumes:
        tags = volume.get("Tags", {})
        tag_combination = tuple((key, tags.get(key)) for key in tag_keys)
        tag_combinations.setdefault(tag_combination, []).append(volume)

    # Manage dashboards
    for tag_combination, volumes in tag_combinations.items():
        if all(value is not None for _, value in tag_combination):
            manage_dashboard(
                tag_combination=tag_combination,
                volumes=volumes,
                cloudwatch=cloudwatch,
                region=args.region,
                dryrun=args.dryrun,
                verbose=args.verbose,
                file_out=args.file_out,
            )


def create_dashboard_body(widgets):
    return {"widgets": widgets}


# The function create_dashboard_widget with adjusted JSON structure
def create_dashboard_widget(volume, region, verbose):
    volume_id = volume["VolumeId"]
    tags = volume["Tags"]
    tag_strings = [f"{key}={value}" for key, value in tags.items()]
    tag_string = ", ".join(tag_strings)
    widget_title = f"{tag_string} {volume_id}"

    # Define metrics
    metrics = [
        # ReadLatency
        {
            "expression": "(m1 / m2) * 1000",
            "label": "ReadLatency",
            "id": "e1",
            "region": region,
            "yAxis": "right",
        },
        # WriteLatency
        {
            "expression": "(m3 / m4) * 1000",
            "label": "WriteLatency",
            "id": "e2",
            "region": region,
            "yAxis": "right",
        },
        [
            "AWS/EBS",
            "VolumeTotalReadTime",
            "VolumeId",
            volume_id,
            {"id": "m1", "region": region},
        ],
        [
            "AWS/EBS",
            "VolumeReadOps",
            "VolumeId",
            volume_id,
            {"id": "m2", "region": region},
        ],
        [
            "AWS/EBS",
            "VolumeTotalWriteTime",
            "VolumeId",
            volume_id,
            {"id": "m3", "region": region},
        ],
        [
            "AWS/EBS",
            "VolumeWriteOps",
            "VolumeId",
            volume_id,
            {"id": "m4", "region": region},
        ],
        [
            "AWS/EBS",
            "VolumeQueueLength",
            "VolumeId",
            volume_id,
            {"id": "m5", "region": region},
        ],
    ]

    num_metrics = sum(1 for metric in metrics if isinstance(metric, list))

    # Define widget properties
    widget_properties = {
        "metrics": metrics,
        "region": region,
        "title": widget_title,
        "yAxis": {"left": {"min": 0}, "right": {"min": 0}},
        "annotations": {
            "horizontal": [
                {
                    "color": "#ff7f0e",
                    "label": "Latency",
                    "value": 0,
                    "yAxis": "right",
                    "fill": "after",
                    "visible": True,
                }
            ]
        },
        "view": "timeSeries",
        "stacked": False,
    }

    widget_contents = {
        "type": "metric",
        "width": 12,
        "height": 5,
        "properties": widget_properties,
    }

    #    if verbose:
    #        print(json.dumps(widget_contents, indent=4))

    return widget_contents, num_metrics


# Function to initialize logging
def initialize_logging(loglevel):
    logging.basicConfig(level=getattr(logging, loglevel.upper()))


def initialize_aws_clients(region):
    try:
        ec2_client = boto3.client("ec2", region_name=region)
        ec2_resource = boto3.resource("ec2", region_name=region)
        cloudwatch = boto3.client("cloudwatch", region_name=region)
        logging.info("Initilized AWS Client")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)  # Stop the script here

    return ec2_client, cloudwatch


def get_valid_aws_regions(ec2_client):
    regions = ec2_client.describe_regions()
    return [region["RegionName"] for region in regions["Regions"]]


def get_tag_data(ebs_volumes):
    tag_data = collections.defaultdict(set)

    for volume in ebs_volumes:
        tags = volume.get("Tags", {})
        for key, value in tags.items():
            tag_data[key].add(value)

    return tag_data


def list_unique_tags(tag_data):
    for key, values in tag_data.items():
        logging.info(f"Tag Key: {key} => Unique Values: {', '.join(values)}")


def list_unique_tag_names(tag_data):
    unique_tag_names = tag_data.keys()
    logging.info(f"Unique Tag Names: {', '.join(unique_tag_names)}")


# Function to gather all EBS Volumes
def get_ebs_volumes(ec2_client):
    paginator = ec2_client.get_paginator("describe_volumes")
    ebs_volumes = []
    for page in paginator.paginate():
        for volume in page["Volumes"]:
            volume_info = {
                "VolumeId": volume["VolumeId"],
                "VolumeName": next(
                    (
                        tag["Value"]
                        for tag in volume.get("Tags", [])
                        if tag["Key"] == "Name"
                    ),
                    None,
                ),
                "Tags": {
                    tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])
                },  # Collect tags
            }
            ebs_volumes.append(volume_info)
            logging.debug(f"Gathered volume: {volume_info}")
    return ebs_volumes


def get_tag_keys_from_args(args):
    if args.tag_keys_file:
        with open(args.tag_keys_file, "r") as f:
            return [line.strip() for line in f.readlines()]
    elif args.tag_keys:
        return args.tag_keys.split(",")
    else:
        logging.error("Either --tag_keys or --tag_keys_file must be provided.")
        sys.exit(1)


def manage_dashboard(
    tag_combination, volumes, cloudwatch, dryrun, region, verbose, file_out=False
):
    total_metric_count = 0
    widgets = []

    for volume in volumes:
        widget, num_metrics = create_dashboard_widget(
            volume=volume, region=region, verbose=verbose
        )
        widgets.append(widget)  # Append only the widget dictionary
        total_metric_count += num_metrics

    total_shards = -(-total_metric_count // DASHBOARD_METRIC_LIMIT)  # Ceiling division

    # Split the widgets into smaller chunks if the total metrics exceed the limit
    current_metric_count = 0
    shard_widgets = []
    shard_index = 1
    for widget in widgets:
        num_metrics = sum(
            1 for metric in widget["properties"]["metrics"] if isinstance(metric, list)
        )
        if current_metric_count + num_metrics > DASHBOARD_METRIC_LIMIT:
            # Create a new shard
            if verbose:
                print(f"Creating shard {shard_index} of {total_shards}\n")

            update_dashboard(
                cloudwatch=cloudwatch,
                volumes=volumes,
                widgets=shard_widgets,
                tag_combination=tag_combination,
                shard_index=shard_index,
                total_shards=total_shards,
                dryrun=dryrun,
                region=region,
                verbose=verbose,
                file_out=file_out,
            )
            shard_widgets = [widget]
            current_metric_count = num_metrics
            shard_index += 1
        else:
            shard_widgets.append(widget)
            current_metric_count += num_metrics

            if verbose:
                print(f"Appending to shard {shard_index} of {total_shards}")
                print(f"Current metric count: {current_metric_count}")

    if shard_widgets:
        # Update the last shard
        update_dashboard(
            cloudwatch=cloudwatch,
            volumes=volumes,
            widgets=shard_widgets,
            tag_combination=tag_combination,
            shard_index=shard_index,
            total_shards=total_shards,
            dryrun=dryrun,
            region=region,
            verbose=verbose,
            file_out=file_out,
        )


def update_dashboard(
    widgets,
    tag_combination,
    shard_index,
    total_shards,
    dryrun,
    region,
    verbose,
    volumes,
    cloudwatch,
    file_out=False,
):
    dashboard_name = (
        f"EBS_{sanitize_name(tag_combination)}_Shard_{shard_index}_of_{total_shards}"
    )

    dashboard_name = f"EBS_{sanitize_name(tag_combination)}_Shard_{shard_index + 1}_of_{total_shards}"
    # Check and truncate dashboard name if it exceeds 255 characters
    if len(dashboard_name) > 255:
        logging.warning(
            f"Truncating dashboard name {dashboard_name} to 255 characters."
        )
        dashboard_name = dashboard_name[:255]

    if verbose:
        logging.info(
            f"\nDashboard name: {dashboard_name}\nShard index: {shard_index}\n"
        )

    widgets = []
    for volume in volumes:
        widget = create_dashboard_widget(volume=volume, region=region, verbose=verbose)
        widgets.append(widget)

    dashboard_body = {"widgets": widgets}

    if file_out:  # Check if --file-out is passed
        file_name = f"{dashboard_name}.json"
        with open(file_name, "w") as f:
            json.dump(dashboard_body, f, indent=4)
        logging.info(f"Dashboard contents written to {file_name}")

    else:
        try:
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body),
            )
            logging.info(f"Dashboard {dashboard_name} updated successfully.")
        except boto3.exceptions.botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "InvalidParameterValue":
                logging.error(
                    f"Invalid parameter value for dashboard {dashboard_name}."
                )
            else:
                logging.error(f"An error occurred: {e.response['Error']['Message']}")

    if verbose:
        volume_list = [vol["VolumeId"] for vol in volumes]
        logging.info(f"\nDashboard {dashboard_name} has volumes: {volume_list}")
        logging.info(
            f"\nDashboard name: {dashboard_name}\nShard index: {shard_index}\n"
        )


def sanitize_name(name):
    return "".join(c if c.isalnum() else "_" for c in str(name))


def parse_args(regions):
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Dashboards for EBS Volumes."
    )
    parser.add_argument(
        "--tag_keys", help="Comma-separated list of tag keys to group dashboards by."
    )
    parser.add_argument(
        "--tag_keys_file",
        help="File containing tag keys to group dashboards by, one per line.",
    )
    parser.add_argument(
        "--file-out",
        action="store_true",
        help="Write dashboard contents to a file",
    )
    parser.add_argument(
        "--list-regions",
        action="store_true",
        help="List available AWS regions",
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        choices=regions,
        help="Specify the AWS Region. Run with --list-regions to get a valid list of regions",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Dry run - do not create/update dashboards",
    )
    parser.add_argument(
        "--list-tag-names",
        action="store_true",
        help="List all unique EBS volue tag names",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="List all EBS volue tag names and a list of unique values",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Prints additional information when running the script",
    )
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
