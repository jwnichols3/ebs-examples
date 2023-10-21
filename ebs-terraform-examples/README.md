# EBS Monitoring using Terraform

## Terraform Alert Automation

The [terraform-ebs-cw-alert-automation](./terraform-ebs-cw-alert-automation) folder contains Terraform script to deploy EventBridge rules to automatically run a Lambda function that creates and deletes CloudWatch alarms for EBS volumes that are determined to be in an Impaired state.

## Terraform Latency Custom Metrics

The [terraform-ebs-cw-latency-custom-metric](./terraform-ebs-cw-latency-custom-metric/) folder contains Terraform script that deploys a Lambda function to collect CloudWatch metrics required to calculate Read and Write Latency per EBS Volume. The script then puts custom Read, Write, and Total Latency metrics per volume. Having the custom metrics for Latency enables the creation of dashboards that leverage dynamic queries (as of Sep 2023, CloudWatch dashboards support a single metric query - latency requires a complex query). There is an example dashboard configuration included that shows the Top 10 Read Latency by volume.
