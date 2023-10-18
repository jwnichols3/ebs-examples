import boto3
from resource_discovery import discover_resources
from utils import setup_logging, handle_error, assume_role


def fetch_alarms_status(session, resources):
    cloudwatch_client = session.client("cloudwatch")
    alarm_statuses = {}

    # Fetch alarms for EC2 instances
    for instance in resources["Instances"]:
        instance_id = instance["Instances"][0]["InstanceId"]
        alarms = cloudwatch_client.describe_alarms(
            AlarmNamePrefix=f"{instance_id}-", StateValue="ALARM"
        )
        alarm_statuses[instance_id] = alarms["MetricAlarms"]

    # Fetch alarms for EBS volumes
    for volume in resources["Volumes"]:
        volume_id = volume["VolumeId"]
        alarms = cloudwatch_client.describe_alarms(
            AlarmNamePrefix=f"{volume_id}-", StateValue="ALARM"
        )
        alarm_statuses[volume_id] = alarms["MetricAlarms"]

    return alarm_statuses


def main():
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


if __name__ == "__main__":
    main()
