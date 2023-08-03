import boto3
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

TIME_PERIOD = 300


def get_metric_statistics(client, volume_id, metric_name):
    response = client.get_metric_statistics(
        Namespace="AWS/EBS",
        MetricName=metric_name,
        Dimensions=[
            {"Name": "VolumeId", "Value": volume_id},
        ],
        StartTime=datetime.utcnow() - timedelta(minutes=5),
        EndTime=datetime.utcnow(),
        Period=TIME_PERIOD,
        Statistics=["Average"],
    )
    return response["Datapoints"][0]["Average"] if response["Datapoints"] else None


def calculate_latency(volume_id, ec2):
    cloudwatch = boto3.client("cloudwatch")

    volume_idle_time = get_metric_statistics(cloudwatch, volume_id, "VolumeIdleTime")

    total_read_time = get_metric_statistics(
        cloudwatch, volume_id, "VolumeTotalReadTime"
    )
    read_ops = get_metric_statistics(cloudwatch, volume_id, "VolumeReadOps")

    total_write_time = get_metric_statistics(
        cloudwatch, volume_id, "VolumeTotalWriteTime"
    )
    write_ops = get_metric_statistics(cloudwatch, volume_id, "VolumeWriteOps")

    read_latency = None
    write_latency = None
    overall_latency = None

    if read_ops is not None and read_ops != 0:
        read_latency = (total_read_time / read_ops) * 1000

    if write_ops is not None and write_ops != 0:
        write_latency = (total_write_time / write_ops) * 1000

    if read_latency is not None and write_latency is not None:
        overall_latency = (read_latency + write_latency) / 2

    volume = ec2.Volume(volume_id)
    instance_id = volume.attachments[0]["InstanceId"] if volume.attachments else None
    instance_state = None
    if instance_id:
        instance = ec2.Instance(instance_id)
        instance_state = instance.state["Name"]

    return [
        volume_id,
        instance_id,
        instance_state,
        volume_idle_time,
        read_ops,
        total_read_time,
        read_latency,
        write_ops,
        total_write_time,
        write_latency,
        overall_latency,
    ]


def main():
    parser = argparse.ArgumentParser(description="Calculate EBS Volume Latency")
    parser.add_argument("--volume-id", help="The volume ID to calculate latency for")
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all volumes, regardless of instance state or attachment",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat the operation",
    )
    args = parser.parse_args()

    for run in range(args.repeat):
        print(f"\nRunning {run+1} of {args.repeat} at {datetime.now()}")
        ec2 = boto3.resource("ec2")
        table_data = []

        if args.volume_id:
            table_data.append(calculate_latency(args.volume_id, ec2))
        else:
            for volume in ec2.volumes.all():
                if args.verbose:
                    print(f"Calculating latency for {volume.id}...")
                volume_data = calculate_latency(volume.id, ec2)
                if args.show_all or (
                    volume_data[2] == "running" and volume_data[1] is not None
                ):
                    table_data.append(volume_data)

        print(
            tabulate(
                table_data,
                headers=[
                    "Volume ID",
                    "EC2 ID",
                    "EC2 State",
                    "IdleTime",
                    "ReadOps",
                    "ReadTime",
                    "ReadLtcy (ms)",
                    "WriteOps",
                    "WriteTime",
                    "WriteLtcy (ms)",
                    "OverallLtcy (ms)",
                ],
            )
        )


if __name__ == "__main__":
    print(f"EBS Latency Calculator - time period {TIME_PERIOD} seconds")
    main()
