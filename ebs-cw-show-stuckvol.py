import argparse
import boto3

# import datetime
from datetime import datetime, timedelta
from prettytable import PrettyTable


def get_volumes(client):
    all_volumes = client.describe_volumes()
    volumes_in_use = [v for v in all_volumes["Volumes"] if v["State"] != "available"]
    return volumes_in_use


def get_instance_name(client, instance_id):
    if not instance_id:
        return None
    instances = client.describe_instances(InstanceIds=[instance_id])
    instance = instances["Reservations"][0]["Instances"][0]
    for tag in instance["Tags"]:
        if tag["Key"] == "Name":
            return tag["Value"]
    return None


def get_metrics(client, volume_id, metric_name):
    metrics = client.get_metric_statistics(
        Namespace="AWS/EBS",
        MetricName=metric_name,
        Dimensions=[
            {"Name": "VolumeId", "Value": volume_id},
        ],
        StartTime=datetime.utcnow() - timedelta(minutes=5),
        EndTime=datetime.utcnow(),
        Period=60,
        Statistics=[
            "Average",
        ],
    )
    return metrics["Datapoints"][0]["Average"] if metrics["Datapoints"] else 0


def is_stuck(read_ops, write_ops, queue_length):
    stuck_vol = (
        True
        if (
            read_ops is not None
            and write_ops is not None
            and read_ops + write_ops == 0
            and queue_length >= 1
        )
        else False
    )

    return stuck_vol


def list_volumes(args):
    client = boto3.client("ec2")
    volumes = get_volumes(client)
    for volume in volumes:
        instance_id = (
            volume["Attachments"][0]["InstanceId"] if volume["Attachments"] else None
        )
        print(
            f"Volume ID: {volume['VolumeId']}, Status: {volume['State']}, Instance: {get_instance_name(client, instance_id)}"
        )


def list_volumes_only(args):
    client = boto3.client("ec2")
    volumes = get_volumes(client)
    for volume in volumes:
        print(f"Volume ID: {volume['VolumeId']}, Status: {volume['State']}")


def print_table(headers, data):
    table = PrettyTable()
    table.field_names = headers
    for row in data:
        table.add_row(row)
    print(table)


def show_dashboard(args):
    client_ec2 = boto3.client("ec2")
    client_cloudwatch = boto3.client("cloudwatch")
    volumes = get_volumes(client_ec2)
    data = []
    for volume in volumes:
        instance_id = (
            volume["Attachments"][0]["InstanceId"] if volume["Attachments"] else None
        )
        m1 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeReadOps")
        m2 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeWriteOps")
        m3 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeQueueLength")
        stuck = is_stuck(m1, m2, m3)
        data.append(
            [
                volume["VolumeId"],
                volume["State"],
                get_instance_name(client_ec2, instance_id),
                "{:8.2f}".format(m1) if m1 is not None else "---",
                "{:8.2f}".format(m2) if m2 is not None else "---",
                "{:.4f}".format(m3) if m3 is not None else "---",
                stuck,
            ]
        )
    print_table(
        [
            "Volume ID",
            "Status",
            "Instance",
            "Read (m1)",
            "Write (m2)",
            "Queue (m3)",
            "VolStuck",
        ],
        data,
    )


def show_dashboard_volume(args):
    client_ec2 = boto3.client("ec2")
    client_cloudwatch = boto3.client("cloudwatch")
    volumes = get_volumes(client_ec2)
    for volume in volumes:
        if volume["VolumeId"] == args.volumeid:
            instance_id = (
                volume["Attachments"][0]["InstanceId"]
                if volume["Attachments"]
                else None
            )
            m1 = get_metrics(client_cloudwatch, volume["VolumeId"])
            m2 = get_metrics(client_cloudwatch, volume["VolumeId"])
            m3 = get_metrics(client_cloudwatch, volume["VolumeId"])
            stuck = is_stuck(m1, m2, m3)
            print(
                f"Volume ID: {volume['VolumeId']}, Status: {volume['State']}, Instance: {get_instance_name(client_ec2, instance_id)}, m1: {m1}, m2: {m2}, m3: {m3}, Stuck: {stuck}"
            )
            break
    else:
        print(f"No volume found with ID: {args.volumeid}")


def show_stuck_only(args):
    client_ec2 = boto3.client("ec2")
    client_cloudwatch = boto3.client("cloudwatch")
    volumes = get_volumes(client_ec2)
    for volume in volumes:
        instance_id = (
            volume["Attachments"][0]["InstanceId"] if volume["Attachments"] else None
        )
        m1 = get_metrics(client_cloudwatch, volume["VolumeId"])
        m2 = get_metrics(client_cloudwatch, volume["VolumeId"])
        m3 = get_metrics(client_cloudwatch, volume["VolumeId"])
        stuck = is_stuck(m1, m2, m3)
        if stuck:
            print(
                f"Volume ID: {volume['VolumeId']}, Status: {volume['State']}, Instance: {get_instance_name(client_ec2, instance_id)}, m1: {m1}, m2: {m2}, m3: {m3}, Stuck: {stuck}"
            )


parser = argparse.ArgumentParser(
    description="EBS Dashboard showing stuck volume status for all EBS volumes that do not have a status of Available."
)
parser.set_defaults(func=show_dashboard)
parser.add_argument(
    "--repeat",
    type=int,
    default=1,
    help="Number of times to repeat the default command",
)
parser.add_argument(
    "--show-status", dest="func", action="store_const", const=show_dashboard
)
args = parser.parse_args()

for i in range(args.repeat):
    print(f"\nRunning iteration {i+1} of {args.repeat} at {datetime.now()}")
    args.func(args)
