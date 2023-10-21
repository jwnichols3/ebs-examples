# Checklist for setup of Cross-Account CloudWatch Data

You can use this checklist to validate your setup.

- [ ] Cross-Account IAM role to collect relevant metadata (EBS, EC2, Tags) using the [Data Gathering Script](./ebs-cw-dashboards-xacct-1-gather-data.py). See [Terraform example](./cross-account-setup-data-gather-terraform/).
- [ ] S3 bucket location to store the Account Info and Collected Data files.
- [ ] Review the resource tagging to verify the tags to use when identifying the resource groupings.
- [ ] Create the Account Info file in CSV format with tabular data. [Example Account Info File](./account-info-example.csv)
- [ ] IAM permissions to run the Data Collection and Dashboard Construction scripts.
- [ ] Setup the CloudWatch Cross-Account Data Flow in the console or with Terraform.
