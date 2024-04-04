# EBS Reporting Examples

This example set is in early development (April 4, 2024) and is not working yet.

## Progress Tracking and TODO Items

[EBS Reporting To Do Items](./TODO.md)

## Overview and Structure

## Example Reports

## Elements and Concepts

Here are some of the elements involved:

- `account-list.csv` - a tabular data structure that has account number, region, account description, and tag name (tag name is how the Dashboards are grouped). This can be a local file or an S3 object.
- `region-list.csv` - a list of regions to cover.
- `Cross Account Role` - a cross-account "readonly "role that has access to gather the EBS and EC2 data (and, eventually other services).
- `Gather Data Python Script` - the script that reads the `account-info.csv` to get the list of accounts, regions, and tags, then connects to the accounts using the `CrossAccountRole` to gather the list of EBS volumes that match the \* `Tag Name` then writes the list to `ebs-data-csv` file. The assumption is the `Tag Name` is present for all dashboard items and is used to identify grouping, such as for Cluster.
- `ebs-report.csv` - the file (tabular csv format) that stores the list of EBS Volumes.

### Account List

The account list is a csv formatted file with a list of AWS Accounts. This Account Information file is local or S3. It has the following fields in CSV format:

`account-number`,`account-description`

[Example Account Info](./account-list-example.csv)

### Gathering and Writing the Data for the Dashboards

The `Gather Data Python Script` cycles through the AWS Accounts and each specified region, collecting the EBS volumes based on the tag-name.

The gather data script leverages A `Cross Account Role` is required to access the target accounts and query for the tagged resources. See below for the relevant IAM configuration.

The `Gather Data Python Script` writes a data file that has the volume-level information in tabular format. The contents of this file is used to construct and update a suite of CloudWatch Dashboards. This file can reside locally or in S3. It has the following fields in csv format:

`Account-Number`,`Account-Description`,`Region`,`Volume-ID`,`Volume-Status`,`Volume-Size`,`Volume-Type`,`Tag-Name`,`Tag-Value`

[Example Data File](./ebs-report-example.py) <= TODO

## Risk and Open Questions

- API Call rate limiting and backoff features

## Pre-Requisits

### Cross Account IAM Role

There is the main account, the one you'll run the scripts from, then there are target accounts that the role will access. This concept is a tad backwards from how the cross-account CloudWatch data flow setup is done.

TODO: Reconcile the naming to match the cross-account CloudWatch data flow setup terminology. Perhaps call the main account running the scripts the "monitoring account" and the target accounts being accessed the "observed accounts".

In the main observability account (or the one that you'll run the scripts from), create an IAM role with the following trust relationship and policies:

TODO: Insert IAM policy statement

In the target accounts (source accounts), add a policy to the cross account role that allows getting relevant information in those accounts.

TODO: Insert IAM policy statement

## Utilities

- [EC2 Deployment Utility for Testing](../ebs-end-to-end-testing/e2e-launch-ec2-instances.py) - this is an example Python script that deploys EC2 instances for testing purposes. Each EC2 and EBS volume deployed is tagged consistently so they can be terminated after testing. There are options for the number of instances, number and type of EBS volumes to attach to each instance, and the ability to deploy to different AWS Regions.
