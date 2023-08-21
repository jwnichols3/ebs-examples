import boto3
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        # Extract the EBS volume ID from the event object
        volume_id = event["detail"]["requestParameters"]["volumeId"]

        # Boto3 client for CloudWatch
        cloudwatch_client = boto3.client("cloudwatch")

        # Delete CloudWatch alarm for the EBS volume
        response = cloudwatch_client.delete_alarms(
            AlarmNames=["ImpairedVol_" + volume_id]
        )

        # Log the response from the delete_alarms call
        logger.info(f"CloudWatch alarm deletion response: {response}")

        return {"statusCode": 200, "body": "Successfully deleted CloudWatch alarm"}

    except Exception as e:
        # Log the error and return a 500 error response
        logger.error(f"An error occurred: {e}")
        return {
            "statusCode": 500,
            "body": "An error occurred while processing the event. See CloudWatch logs for details.",
        }
