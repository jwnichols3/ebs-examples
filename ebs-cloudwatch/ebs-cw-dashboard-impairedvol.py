import boto3
import json
import argparse
import logging
import sys


def main():
    args = parse_args()

    initilize_logging(args=args)

    cloudwatch = initialize_aws_clients(region=args.region)

    if args.read:
        read_dashboard(cloudwatch=cloudwatch)
    else:
        update_dashboard(cloudwatch=cloudwatch, verbose=args.verbose)


def initilize_logging(args):
    # Initialize logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


def get_alarms(cloudwatch):
    # Describe alarms
    alarms = cloudwatch.describe_alarms(AlarmNamePrefix="ImpairedVol_")

    # Collect the ARNs of the alarms that start with "ImpairedVol_"
    return [alarm["AlarmArn"] for alarm in alarms["MetricAlarms"]]


def update_dashboard(cloudwatch, verbose):
    # Get current alarms
    current_alarms = get_alarms(cloudwatch=cloudwatch)

    # Initialize widget list
    widgets = []

    # Add individual widgets for each alarm
    x_position = 0
    y_position = 0
    for alarm in current_alarms:
        widget = {
            "type": "alarm",
            "x": x_position,
            "y": y_position,
            "width": 6,
            "height": 6,
            "properties": {
                "title": f"Impaired Volume: {alarm.split(':')[-1]}",
                "alarms": [alarm],
            },
        }
        widgets.append(widget)

        # Update positions for the next widget
        x_position += 6
        if x_position >= 24:  # Assuming dashboard width of 24 units
            x_position = 0
            y_position += 6  # Move to the next row

    # Create or update the dashboard
    dashboard_body = {"widgets": widgets}
    cloudwatch.put_dashboard(
        DashboardName="MyDashboard", DashboardBody=json.dumps(dashboard_body)
    )

    print("Dashboard updated successfully.")


def read_dashboard(cloudwatch):
    try:
        # Get the existing dashboard
        dashboard = cloudwatch.get_dashboard(DashboardName="MyDashboard")
        dashboard_body = json.loads(dashboard["DashboardBody"])
        print("Existing Dashboard Content: ")
        print(json.dumps(dashboard_body, indent=2))

        # Get alarms from the dashboard
        dashboard_alarms = dashboard_body["widgets"][0]["properties"]["alarms"]

        # Get current alarms
        current_alarms = get_alarms(cloudwatch=cloudwatch)

        # Find alarms that are not on the dashboard
        missing_alarms = set(current_alarms) - set(dashboard_alarms)
        if missing_alarms:
            print("\nAlarms that do not exist on the dashboard:")
            for alarm in missing_alarms:
                print(alarm)
        else:
            print("\nAll alarms are present on the dashboard.")

    except cloudwatch.exceptions.ResourceNotFoundException:
        print("Dashboard MyDashboard does not exist.")


def initialize_aws_clients(region):
    try:
        cloudwatch = boto3.client("cloudwatch", region_name=region)
        logging.info(f"Initilized AWS Client in region {region}")
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        sys.exit(1)  # Stop the script here

    return cloudwatch


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch Dashboard for EBS Impaired Volume."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print details of boto3 calls."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print debug level logging."
    )
    parser.add_argument("--region", default="us-west-2", help="AWS region name.")
    parser.add_argument(
        "--read",
        action="store_true",
        help="Read the content of the existing dashboard.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
