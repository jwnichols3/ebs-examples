import argparse
import boto3
from datetime import datetime, timedelta
from tabulate import tabulate

# from prettytable import PrettyTable

PAGINATION_COUNT = 300  # Set the desired value here


def print_table(headers, data, style):
    print(tabulate(data, headers=headers, tablefmt=style))


def get_volumes(client):
    all_volumes = []
    paginator = client.get_paginator("describe_volumes")
    for page in paginator.paginate(MaxResults=PAGINATION_COUNT):
        volumes_in_use = [v for v in page["Volumes"] if v["State"] != "available"]
        all_volumes.extend(volumes_in_use)
    return all_volumes


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


def is_impaired(read_ops, write_ops, queue_length):
    impaired_vol = (
        True
        if (
            read_ops is not None
            and write_ops is not None
            and read_ops + write_ops == 0
            and queue_length > 0
        )
        else False
    )

    return impaired_vol


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


def show_dashboard(args):
    client_ec2 = boto3.client("ec2")
    client_cloudwatch = boto3.client("cloudwatch")
    if args.verbose:
        print(f"Getting volumes.")
    volumes = get_volumes(client_ec2)
    data = []
    for volume in volumes:
        if args.verbose:
            print(f"Getting information for {volume['VolumeId']}.")
        instance_id = (
            volume["Attachments"][0]["InstanceId"] if volume["Attachments"] else None
        )
        m1 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeReadOps")
        m2 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeWriteOps")
        m3 = get_metrics(client_cloudwatch, volume["VolumeId"], "VolumeQueueLength")
        impaired = is_impaired(m1, m2, m3)
        data.append(
            [
                volume["VolumeId"],
                volume["State"],
                get_instance_name(client_ec2, instance_id),
                "{:8.2f}".format(m1) if m1 is not None else "---",
                "{:8.2f}".format(m2) if m2 is not None else "---",
                "{:.4f}".format(m3) if m3 is not None else "---",
                impaired,
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
            "VolImpaired",
        ],
        data,
        args.style,
    )


parser = argparse.ArgumentParser(
    description="EBS Dashboard showing impaired volume status for all EBS volumes that do not have a status of Available."
)
parser.set_defaults(func=show_dashboard)
parser.add_argument(
    "--repeat",
    type=int,
    default=1,
    help="Number of times to repeat.",
)
parser.add_argument(
    "--style",
    type=str,
    choices=["tsv", "simple", "pretty", "plain", "github", "grid", "fancy"],
    default="simple",
    help="Table style format. Valid options are tsv, simple, pretty, plain, github, grid, fancy. The default is simple",
)
parser.add_argument(
    "--show-status",
    dest="func",
    action="store_const",
    help="(default option) Show a dashboard of EBS volumes with metrics indicating a impaired volume.",
    const=show_dashboard,
)
parser.add_argument("--verbose", action="store_true", help="Print verbsoe output.")
args = parser.parse_args()

for i in range(args.repeat):
    print(f"\nRunning iteration {i+1} of {args.repeat} at {datetime.now()}")
    args.func(args)
