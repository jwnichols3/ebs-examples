# Terraform EBS Alert Automation

This folder contains Terraform configuration to deploy Lambda functions and EventBridge rules to automatically create and delete CloudWatch alarms for EBS volumes.

## NEW DEPLOYMENT

You will want to delete the file `.terraform.lock.hcl` before running `terraform apply` to ensure a clean deployment.

Be sure to zip the two python files into separate files before running `terraform apply`.

Here are samples of how to zip the files using zip:

`zip -r ebs-lambda-cw-alarm-impairedvol-create.zip ebs-lambda-cw-alarm-impairedvol-create.py`

`zip -r ebs-lambda-cw-alarm-impairedvol-delete.zip ebs-lambda-cw-alarm-impairedvol-delete.py`

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
- In the [systems-manager-automation](../systems-manager-automation/) folder is an alternative approach using SSM Automation Documents instead of Laambda. There is also a Python script to [test end-to-end workflow](../systems-manager-automation/ebs-cw_events-ssm-end2end.py) that you can use to validate this deployment works as expected.
