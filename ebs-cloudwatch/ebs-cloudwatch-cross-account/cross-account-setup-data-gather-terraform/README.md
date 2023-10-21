# Overview of Cross Account Setup for CloudWatch Data Gathering using Terraform

These Terraform scripts create IAM roles in the target accounts to allow the main account to assume a role and query data from services like CloudWatch, EC2, and EBS. The roles are given a minimum set of permissions needed to query metrics and tags.

Terraform probably has a more elegant way to deploy this. For the sake of time, this is considered technical debt to figure out. There is a TF project per account.

The folder structure is:

- [main-account](./main-account/)
- [target-account-1](./target-account-1/)
- [target-account-2](./target-account-2/)
- [target-account-3](./target-account-3/)
- [target-account-4](./target-account-4/)
- etc

## Concepts

- _Main Account_ = the account that will collect metrics from other accounts.
- _Target Account_ = the account that the main account will collect metrics from. The main account will assume a cross account role in the target account to retrieve data.

## Usage

In each account, edit the `terraform.tfvars` and edit the corresponging values:

- _target-account-ids_ = list of target accounts found in the main-account tfvars file.
- _main-account_-id = the main account id found in each of the target-account tfvars files

## To Do Tracking

[Cross Account Setup for Data Gathering To Do List](./TODO.md)
