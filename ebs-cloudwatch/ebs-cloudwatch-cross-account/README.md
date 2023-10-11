# EBS CloudWatch Monitoring - Cross Account and Cross Region

[CloudWatch Cross Account Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)

## Overview

Collecting and storing Account Information in a local or S3 file that includes the following fields in CSV format:

`account-number`,`region`,`account-description`,'tag-name`

## Pre-Requisits

- [CloudWatch Cross-Account, Cross Region setup](./cross-account-setup-cloudwatch/cross-account-setup-cloudwatch.md).
- IAM Policies to gather the EBS, EC2, and CloudWatch metadata. [Terraform Version](./cross-account-setup-data-gather-terraform/)

## Utilities

- [EC2 Deployment Utility for Testing](../../ebs-end-to-end-testing/e2e-launch-ec2-instances.py)]

### To be developed

`ebs-xacct-util.py` - utility to list volumes, tag, etc across all included AWS Accounts.

`ebs-cw-xacct-latency.py` - utility to list CW metrics that make up read/write latency across all EBS volumes across all AWS Accounts.

`ebs-cw-xacct-impairedvol.py` - utility to list CW metrics that make up Impaired Volume across all EBS volumes across all AWS Accounts.

## Dashboards

### CloudWatch Dashboard Considerations

- Metrics per Dashboard
- Metrics per Graph

### Construction by Tag

The hypothesis is that for larger deployments, the way to manage EBS dashboards and alarms is by leveraging Tags to navigate. With a multi-account strategy

### Dashboard Navigation

A singluar Navigation Dashboard called **EBS_NAV** will have widgets with link to each sub-dashboard

A secondary navigation dashboard by Account & Region

_EBS_NAV_

\_EBS_NAV_Account Description

\_EBS_NAV_Account Description_Region

\_EBS_NAV_Region

\_EBS_NAV_Region_Account Description

\_EBS_NAV_Region_Account Description_Account Number

### Sub-Dashboard

Structure:
[Link to _EBS_NAV_ Dashboard]
[Widget with each EBS Volume with key EBS Metrics] (assuming each Widget has less than 500 metrics)

Dashboard sharding will happen when the Dashboard reaches the maxium number of metrics per dashboard.

Name:
EBS*<TagName>*<TagValue>_<#>_<AcctName>\_<AcctNum> - where <#> is the shard number

EBS*<TagName>*<TagValue>_<VolId>_<AcctName>\_<AcctNum>
