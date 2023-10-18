import json
import boto3
from resource_discovery import discover_resources
from alarm_manager import fetch_alarms_status
from utils import setup_logging, handle_error, assume_role


def generate_dashboard_body(cluster_name, instances, volumes, alarms_status):
    widgets = []

    # Generate widgets for EC2 instances
    for instance in instances:
        instance_id = instance["Instances"][0]["InstanceId"]
        widget = {
            "type": "text",
            "x": 0,
            "y": len(widgets) * 3,  # Adjust position for each new widget
            "width": 24,
            "height": 3,
            "properties": {
                "markdown": f"## Instance: {instance_id}\nAlarm Status: {alarms_status.get(instance_id, 'OK')}"
            },
        }
        widgets.append(widget)

    # Generate widgets for EBS volumes
    for volume in volumes:
        volume_id = volume["VolumeId"]
        widget = {
            "type": "text",
            "x": 0,
            "y": len(widgets) * 3,  # Adjust position for each new widget
            "width": 24,
            "height": 3,
            "properties": {
                "markdown": f"## Volume: {volume_id}\nAlarm Status: {alarms_status.get(volume_id, 'OK')}"
            },
        }
        widgets.append(widget)

    dashboard_body = {"widgets": widgets}

    return json.dumps(dashboard_body)


def create_update_dashboard(session, cluster_name, dashboard_body):
    cloudwatch_client = session.client("cloudwatch")

    dashboard_name = f"{cluster_name}-Dashboard"
    response = cloudwatch_client.put_dashboard(
        DashboardName=dashboard_name, DashboardBody=dashboard_body
    )

    return response


def manage_dashboard(
    account_id, role_name, region, cluster_name, instances, volumes, alarms_status
):
    session = assume_role(
        account_id, role_name, region
    )  # Assuming assume_role is imported from resource_discovery.py or defined in this script
    dashboard_body = generate_dashboard_body(
        cluster_name, instances, volumes, alarms_status
    )
    response = create_update_dashboard(session, cluster_name, dashboard_body)
    return response


if __name__ == "__main__":
    account_id = "357044226454"
    role_name = "CrossAccountObservabilityRole"
    region = "us-west-2"
    cluster_name = "YourClusterName"

    # Discover resources
    instances, volumes = discover_resources(account_id, role_name, region, cluster_name)

    # Assume role and create a session
    session = assume_role(account_id, role_name, region)

    # Fetch alarm statuses
    resources = {"Instances": instances, "Volumes": volumes}
    alarm_statuses = fetch_alarms_status(session, resources)

    # Output alarm statuses
    print(alarm_statuses)

    response = manage_dashboard(
        account_id, role_name, region, cluster_name, instances, volumes, alarm_statuses
    )
    print(response)
