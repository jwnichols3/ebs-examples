import boto3
import logging
import os

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        # Extract the EBS volume ID from the event object
        volume_id = event["detail"]["responseElements"]["volumeId"]

        # SNS topic ARN from environment variables
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

        # Log the response from the put_metric_alarm call
        logger.info(f"CloudWatch alarm response: {response}")

        return {"statusCode": 200, "body": response}

    except Exception as e:
        # Log the error and return a 500 error response
        logger.info(f"Received event: {event}")
        logger.error(f"An error occurred: {e}")
        return {
            "statusCode": 500,
            "body": "An error occurred while processing the event. See CloudWatch Logs for details.",
        }
