import boto3
import os


def lambda_handler(event, context):
    # Extract the EBS volume ID from the event object
    volume_id = event["detail"]["requestParameters"]["volumeId"]

    # SNS topic for alarm actions
    # sns_topic_arn = "arn:aws:sns:us-west-2:338557412966:ebs_alarms"
    sns_topic_arn = os.environ["SNS_TOPIC_ARN"]

    # Boto3 client for CloudWatch
    cloudwatch_client = boto3.client("cloudwatch")

    # Create or update CloudWatch alarm for the EBS volume
    response = cloudwatch_client.put_metric_alarm(
        AlarmName="ImpairedVol_" + volume_id,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        EvaluationPeriods=1,
        MetricName="VolumeIdleTime",
        Namespace="AWS/EBS",
        Period=300,
        Statistic="Average",
        Threshold=0.01,
        ActionsEnabled=True,
        AlarmActions=[sns_topic_arn],
        AlarmDescription="Alarm for EBS volume " + volume_id,
        Dimensions=[
            {"Name": "VolumeId", "Value": volume_id},
        ],
        Unit="Seconds",
    )

    return {"statusCode": 200, "body": response}
