# Terraform EBS Alert Automation

This folder contains Terraform configuration to deploy Lambda functions and EventBridge rules to automatically create and delete CloudWatch alarms for EBS volumes.

## Contents

The following files are included:

- `main.tf` - Main Terraform configuration
- `ebs-lambda-cw-alarm-impairedvol-create.zip` - Lambda function code to create CloudWatch alarms
- `ebs-lambda-cw-alarm-impairedvol-delete.zip` - Lambda function code to delete CloudWatch alarms

## Components

The main.tf file deploys the following components:

- IAM role and policy for Lambda
- SNS topic for Lambda to publish alerts
- Lambda function to create alarms
- Lambda function to delete alarms
- EventBridge rule to invoke create function on EBS volume creation
- EventBridge rule to invoke delete function on EBS volume deletion
- SNS subscription to send emails for alarms

## Usage

1. Configure AWS credentials
2. Run `terraform init`
3. Run `terraform apply` to deploy

## Additional Info

- This is example code and not intended for production use without modification.
- Lambda functions are packaged as ZIP files containing Python code
- Lambda executes when EventBridge rules match EBS API calls via CloudTrail
