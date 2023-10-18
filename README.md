# ebs-examples

## TODO

[To do and Feature Tracking](./TODO.md)

## Overview

This repository contains Python scripts that demonstrate the use of AWS SDK (boto3) to interact with Amazon EBS volumes and AWS CloudWatch. These scripts provide a variety of functionality, including creating CloudWatch Alarms for "impaired" volumes, calculating and displaying the read, write, and overall latency for EBS volumes, and creating a CloudWatch Dashboard for EBS latency metrics.

In addition to the Python scripts, there are AWS Systems Manager automations that do similar functions. See more in the [SSM README](./systems-manager-automation-ebs-cw-alarms/)

## Updates

- _Aug 28, 2023_ Moved the EBS CloudWatch scripts to the [ebs-cloudwatch](./ebs-cloudwatch/) folder.

- _Sept 12, 2023_ New cross-account, cross-region CloudWatch Dashboards script that aggregates metrics from multiple AWS accounts and regions into a single dashboard for easier monitoring. [CW Dashboard Cross Account, Cross Region README](./ebs-cloudwatch/ebs-cloudwatch-cross-account/)

## Disclaimer

Please note: These scripts are intended for educational purposes and are not recommended for production use. Always test scripts in a controlled environment before using them in a production capacity. There is minimum error handling implemented and not all scenarious are accounted for such as scale, access controls, and input validation. There is an inherent assumption that you have a way to run these scripts on a system that has access to the AWS account in question and the required privileges.

## Resources in this Repo

### EBS CloudWatch Scripts

The [ebs-cloudwatch](./ebs-cloudwatch/) folder contains the stand-alone Python scripts to update CloudWatch Alarms, show if any EBS volumes are in the Impaired status, show latency metrics, create custom CloudWatch metrics for read and write latency, example CloudWatch dashboards, and more.

#### EBS CloudWatch Cross-Account, Cross-Region Scripts

The [ebs-cloudwatch/ebs-cloudwatch-cross-account/](./ebs-cloudwatch/ebs-cloudwatch-cross-account/) folder contains Python scripts to aggregate CloudWatch metrics from multiple AWS accounts and regions into a suite of CloudWatch Dashboards using the boto3 library. The scripts query AWS resource metadata across accounts and regions, process the results, and creates/updates a suite of CloudWatch Dashboards that reflect the different Applications (based on Tag Names) across Regions and Accounts.

### Systems Manager Automation (CloudWatch EBS ImpairedVol Alarms)

The [systems-manager-automation-ebs-cw-alarms](./systems-manager-automation-ebs-cw-alarms) folder contains examples of using AWS Systems Manager Automation to create and delete CloudWatch Alarms for EBS Volumes in an Impaired state. This includes an end-to-end test script that is usable with both the Systems Manager examples and the Terraform examples.

### Terraform Alert Automation

The [terraform-ebs-cw-alert-automation](./terraform-ebs-cw-alert-automation) folder contains Terraform script to deploy EventBridge rules to automatically run a Lambda function that creates and deletes CloudWatch alarms for EBS volumes that are determined to be in an Impaired state.

### Terraform Latency Custom Metrics

The [terraform-ebs-cw-latency-custom-metric](./terraform-ebs-cw-latency-custom-metric/) folder contains Terraform script that deploys a Lambda function to collect CloudWatch metrics required to calculate Read and Write Latency per EBS Volume. The script then puts custom Read, Write, and Total Latency metrics per volume. Having the custom metrics for Latency enables the creation of dashboards that leverage dynamic queries (as of Sep 2023, CloudWatch dashboards support a single metric query - latency requires a complex query). There is an example dashboard configuration included that shows the Top 10 Read Latency by volume.

### EBS Mini Load Testing and Fault Injection Testing

The [ebs-end-to-end-testing](./ebs-end-to-end-testing/) folder contains scripts to launch EC2 instances with EBS volumes. There are examples of using `fio` to perform load tests against EBS volumes by reading and writing random data. This allows validating that CloudWatch alarms and dashboards react as expected when volumes become impaired. There is a subfolder that includes the AWS Fault Injection Simulator configuration to inject faults. Note: this is going through revisions to do end-to-end testing for CloudWatch Alarm deploymennt, and more.

## EBS Utils Python Script

`ebs-utils.py`
