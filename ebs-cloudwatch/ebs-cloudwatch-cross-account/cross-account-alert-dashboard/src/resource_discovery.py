import boto3
from utils import setup_logging, handle_error, assume_role


def discover_ec2_instances(session, cluster_name):
    ec2_client = session.client("ec2")
    instances = ec2_client.describe_instances(
        Filters=[{"Name": "tag:ClusterName", "Values": [cluster_name]}]
    )
    return instances["Reservations"]


def discover_ebs_volumes(session, cluster_name):
    ec2_client = session.client("ec2")
    volumes = ec2_client.describe_volumes(
        Filters=[{"Name": "tag:ClusterName", "Values": [cluster_name]}]
    )
    return volumes["Volumes"]


def discover_resources(account_id, role_name, region, cluster_name):
    session = assume_role(account_id, role_name, region)
    instances = discover_ec2_instances(session, cluster_name)
    volumes = discover_ebs_volumes(session, cluster_name)
    return instances, volumes


if __name__ == "__main__":
    account_id = "357044226454"
    role_name = "CrossAccountObservabilityRole"
    region = "us-west-2"
    cluster_name = "YourClusterName"
    instances, volumes = discover_resources(account_id, role_name, region, cluster_name)
    print(f"Instances: {instances}")
    print(f"Volumes: {volumes}")
