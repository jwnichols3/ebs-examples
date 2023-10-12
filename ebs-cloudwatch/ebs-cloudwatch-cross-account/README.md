# EBS CloudWatch Monitoring - Cross Account and Cross Region

## Progress Tracking (MVP)

- [x] Cross-Account Access via IAM [Terraform](./cross-account-setup-data-gather-terraform/)
- [x] Cross-Account CW data flow [Information](./cross-account-setup-cloudwatch/cross-account-setup-cloudwatch.md)
- [x] Collecting EBS Volumes based on a list of accounts and tags [MVP Python Script](./part1-collect-data-with-tags.py)
- [x] Writing the EBS Volume data to a file for use by the CW Dashboard construction script [MVP Python Script](./part1-collect-data-with-tags.py)
- [ ] CW Dashboard construction script
- [ ] CW Dashboard clean up script
- [ ] CW Dashboard Navigation Dashboard

## Progress Tracking (Post-MVP)

- [ ] Automation of CW Cross-Account data flow setup.
- [ ] Mechanisms to trigger the CW Dashboard scripts
- [ ] Lambda versions of the script(s)

## Overview

[Setting up CloudWatch Cross Account Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)

The elements of this script include:

- Collecting and storing Account Information in a local or S3 file that includes the following fields in CSV format:

`account-number`,`region`,`account-description`,'tag-name`

- Creating a file that has the volume-level information used to construct and update a suite of CW Dashboards. This volume-level file has the following fields in csv format:

`Account-Number`,`Account-Description`,`Region`,`Volume-ID`,`Volume-Status`,`Volume-Size`,`Volume-Type`,`Tag-Name`,`Tag-Value`

- Reading the volume-level file and constructing / updating the CW Dashboard collection.
- Cleaning up any dashboards that are no longer needed.

## Risk and Open Questions

- Figuring out how to deploy the cross-account, cross-region CW capabilities using automation.
- Frequency and Impact of Dashboard updates - if these dashboards are actively used, what happens when the content is changed or the Dashboard deleted
- Mechanisms to trigger the script(s) - options include SSM Automation (by an event or on a scheduler), CRON jobs on a EKS Pod
- Expand behond EBS to other services, such as EC2, EKS, Network, and more.

## Pre-Requisits

- [CloudWatch Cross-Account, Cross Region setup](./cross-account-setup-cloudwatch/cross-account-setup-cloudwatch.md).
- IAM Policies to gather the EBS, EC2, and CloudWatch metadata. [Terraform Version](./cross-account-setup-data-gather-terraform/)

## Utilities

- [EC2 Deployment Utility for Testing](../../ebs-end-to-end-testing/e2e-launch-ec2-instances.py)]

### Utilities to be developed

`ebs-xacct-util.py` - utility to list volumes, tag, etc across all included AWS Accounts.

`ebs-cw-xacct-latency.py` - utility to list CW metrics that make up read/write latency across all EBS volumes across all AWS Accounts.

`ebs-cw-xacct-impairedvol.py` - utility to list CW metrics that make up Impaired Volume across all EBS volumes across all AWS Accounts.

## Dashboards

The CloudWatch Dashboard "Ecosystem" is a collection based on the Account Number, Region, and Specific Tag Names.

At the top level if a "navigation" dashboard that links to the different sub-dashboards.

Each sub-dashboard has a unique combination of Account Number, Region, and Tag Name/Value. For scaling purposes, the dashboard limits are taken into consideration. Currently (Oct 2023) there is a 2500 metric limit per CW Dashboard. The logic will "shard" the dashboards.

For example, as sub-dashboard might look something like:

`EBS_ClusterName_Cluster123_1_us-west-2_123456`

### CloudWatch Dashboard Considerations

The constraints for CloudWatch Dashboards exist. Currently there are two main constraints to consider:

- Metrics per Dashboard
- Metrics per Graph

For this effort, I am going to exit the script if the metrics per graph exceed the limit. For the Metrics per Dashboard, the script will shard the dashboards.

### Construction by Tag

The hypothesis is that for larger deployments, the way to manage EBS dashboards and alarms is by leveraging Tags to navigate. With a multi-account strategy, the tags become critical to the management of the Dashboards.

The assumption is the central account list will include all of the relevant Tag Names for each account. For example, if an account has ClusterName as a tag - that is one entry on the account list. If there is a second tag for the same account called Environment, that will be a separate line item in the Account List. The term for this concept is tabular data - every row has all data elements.

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
