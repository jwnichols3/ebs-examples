# ebs-examples

## TODO and Feature Tracking

[To do and Feature Tracking](./TODO.md)

## Overview

This repository contains Python scripts that demonstrate the use of AWS SDK (boto3) to interact with Amazon EBS volumes and AWS CloudWatch. These scripts provide a variety of functionality, including creating CloudWatch Alarms for "impaired" volumes, calculating and displaying the read, write, and overall latency for EBS volumes, and creating a CloudWatch Dashboard for EBS latency metrics.

In addition to the Python scripts, there are AWS Systems Manager automations that do similar functions. See more in the [SSM README](./systems-manager-automation-ebs-cw-alarms/)

For more CloudWatch examples, see the [CW Examples Github Repo](https://github.com/jwnichols3/cw-examples)

## Updates

- _Aug 28, 2023_ Moved the EBS CloudWatch scripts to the [ebs-cloudwatch](./ebs-cloudwatch/) folder.

- _Sept 12, 2023_ New cross-account, cross-region CloudWatch Dashboards script that aggregates metrics from multiple AWS accounts and regions into a single dashboard for easier monitoring. [CW Dashboard Cross Account, Cross Region README](./ebs-cloudwatch/ebs-cloudwatch-cross-account/)
- _Oct 10, 2023_ Added support for aggregating EBS volume impairment metrics (status checks) across accounts and regions in the [cross-account dashboard](./ebs-cloudwatch/ebs-cloudwatch-cross-account/).
- _Oct 20, 2023_ Converged the EBS CloudWatch Alarm scripts into a single script `ebs-cw-alarm-manager.py` ([README](./ebs-cloudwatch/README-ebs-cw-alarm-manager.md)), effectively retiring the standalone `impairedvol` and `latency` alarm scripts. Also restructured the REPO to be more logically arranged.

## Disclaimer

Please note: These scripts are intended for educational purposes and are not recommended for production use. Always test scripts in a controlled environment before using them in a production capacity. There is minimum error handling implemented and not all scenarious are accounted for such as scale, access controls, and input validation. There is an inherent assumption that you have a way to run these scripts on a system that has access to the AWS account in question and the required privileges.

## Resources in this Repo

_Philosophy_: my philosophy when creating these scripts and examples is to create stand-alone examples. This might make for inefficient code (e.g. functionality repeated across several scripts). The purpose behind this is to make each script a contained thing you can review, understand, and leverage the parts that make sense to you. You might see some refactoring over time that reflects more effective Python coding techniques, but I will usually stop short of ultra-sophisticated Python, mostly in care of my future self who will look at this code and find it easy to understand, modify and reuse parts of as needed instead of re-learning the sophisticated Python concepts.

### EBS CloudWatch Scripts

The [ebs-cloudwatch](./ebs-cloudwatch/) folder contains Python scripts to deploy and manage CloudWatch Alarms, CloudWatch Dashboards, CloudWatch Custom Metrics, and CLI-based scripts.

#### EBS CloudWatch Cross-Account, Cross-Region Scripts

The [ebs-cloudwatch/ebs-cloudwatch-cross-account/](./ebs-cloudwatch/ebs-cloudwatch-cross-account/) folder contains Python scripts to aggregate CloudWatch metrics from multiple AWS accounts and regions into a suite of CloudWatch Dashboards using the boto3 library. The scripts query AWS resource metadata across accounts and regions, process the results, and creates/updates a suite of CloudWatch Dashboards that reflect the different Applications (based on Tag Names) across Regions and Accounts.

### EBS-Centric Systems Manager Automation Examples

In the [Systems Manager examples folder](./ebs-systems-manager-examples) are examples of leveraging AWS Systems Manager to deploy and manage EBS Monitoring and Alerts.

### EBS-Based Terraform Examples

In the [Terraform Examples](./ebs-terraform-examples) folder there are examples of deploying alerts and monitoring using Terraform scripts.

### EBS End-to-End Testing

The [ebs-end-to-end-testing](./ebs-end-to-end-testing/) folder contains scripts to launch EC2 instances with EBS volumes. There are examples of using `fio` to perform load tests against EBS volumes by reading and writing random data. This allows validating that CloudWatch alarms and dashboards react as expected when volumes become impaired.

### EBS Fauilt Injection (FIS) Testing

The [EBS FIS folder](./ebs-fault-injection-fis/) includes the AWS Fault Injection Simulator configuration to inject faults. Note: this is going through revisions to do end-to-end testing for CloudWatch Alarm deploymennt, and more.

## EBS Utils Python Script

[`ebs-utilitiess.py`](./ebs-utilities.py)

A general purpose script that does things like list tag values for volumes, gets a list of volumes, etc. This is useful for troubleshooting and testing.
