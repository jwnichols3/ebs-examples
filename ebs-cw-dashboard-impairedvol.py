import boto3
import json
import argparse


def get_alarms():
    # Create a CloudWatch client
    cloudwatch = boto3.client("cloudwatch")

    # Describe alarms
    alarms = cloudwatch.describe_alarms(AlarmNamePrefix="ImpairedVol_")

    # Collect the ARNs of the alarms that start with "ImpairedVol_"
    return [alarm["AlarmArn"] for alarm in alarms["MetricAlarms"]]


def update_dashboard(verbose):
    # Create a CloudWatch client
    cloudwatch = boto3.client("cloudwatch")

    # Get current alarms
    current_alarms = get_alarms()

    try:
        # Get the existing dashboard
        dashboard = cloudwatch.get_dashboard(DashboardName="MyDashboard")
        dashboard_body = json.loads(dashboard["DashboardBody"])
        # Get alarms from the existing dashboard
        dashboard_alarms = dashboard_body["widgets"][0]["properties"]["alarms"]
    except cloudwatch.exceptions.ResourceNotFoundException:
        # No existing dashboard, so start with no alarms
        dashboard_alarms = []

    # Find alarms that are not on the dashboard
    new_alarms = set(current_alarms) - set(dashboard_alarms)
    if new_alarms:
        print("\nAdding the following alarms to the dashboard:")
        for alarm in new_alarms:
            print(alarm)

    # Collect the ARNs of the alarms that start with "ImpairedVol_"
    alarm_arns = current_alarms

    # Define the dashboard body
    dashboard_body = {
        "widgets": [
            {
                "type": "alarm",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {"title": "Impaired Volume Alarms", "alarms": alarm_arns},
            }
        ]
    }

    # Create or update the dashboard
    cloudwatch.put_dashboard(
        DashboardName="MyDashboard", DashboardBody=json.dumps(dashboard_body)
    )

    print("Dashboard updated successfully.")


def read_dashboard():
    # Create a CloudWatch client
    cloudwatch = boto3.client("cloudwatch")

    try:
        # Get the existing dashboard
        dashboard = cloudwatch.get_dashboard(DashboardName="MyDashboard")
        dashboard_body = json.loads(dashboard["DashboardBody"])
        print("Existing Dashboard Content: ")
        print(json.dumps(dashboard_body, indent=2))

        # Get alarms from the dashboard
        dashboard_alarms = dashboard_body["widgets"][0]["properties"]["alarms"]

        # Get current alarms
        current_alarms = get_alarms()

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage CloudWatch Dashboard.")
    parser.add_argument(
        "--verbose", action="store_true", help="Print details of boto3 calls."
    )
    parser.add_argument(
        "--read",
        action="store_true",
        help="Read the content of the existing dashboard.",
    )
    args = parser.parse_args()

    if args.read:
        read_dashboard()
    else:
        update_dashboard(args.verbose)
