# Cross-Account CW Dashboard Progress Tracking and TODO

- [ ] All: Max length of all the things. (255 for Title, etc)
- [x] Dashboards: Sharding on Dashboards that exceed maxiumum metrics per dashboard
- [x] Dashboards: Add a Return to Main Nav widget on each dashboard.
- [ ] All: Reduce cognitive load on some of the functions.
- [ ] All: Include IAM Role and Policy examples in the [README](./README.md)
- [ ] All: Testing of negitive cases (wrong data, access, etc)
- [ ] Main Nav: Error Check: Check to see if Main Nav exceeding max height on a widget.
- [ ] Main Nav: Feature: Create a single widget per Account
- [ ] Main Nav: Feature: Create a single widget per Region

## Progress Tracking (MVP)

- [x] Cross-Account Access via IAM [Terraform](./cross-account-setup-data-gather-terraform/)
- [x] Cross-Account CloudWatch data flow [Information](./cross-account-setup-cloudwatch/cross-account-setup-cloudwatch.md)
- [x] Collecting EBS Volume data based on the Account-Info file and writing the gathered data to a file for use by the CloudWatch Dashboard construction script [MVP Data Gathering Python Script](./ebs-cw-dashboards-xacct-1-gather-data.py)
- [x] CloudWatch Dashboard construction script [MVP Construction Python Script](./ebs-cw-dashboards-xacct-2-construct.py)
  - [x] Create the CloudWatch Dashboards
  - [x] Shard the Dashboard when exceeding CloudWatch Dashboard limits.
  - [x] CloudWatch Dashboard Navigation Dashboard
- [x] CloudWatch Dashboard clean up script ~[MVP Python Script](./ebs-cw-dashboards-xacct-3-cleanup.py)~ Incorporated into [MVP Construction Script](./ebs-cw-dashboards-xacct-2-construct.py)

#### Main Navigation Dashboard Updates

In addition to the full list, create widgets based on:

- [ ] Region
- [ ] Account

## Progress Tracking (Post-MVP)

- [ ] Automation of CloudWatch Cross-Account data flow setup.
- [ ] Enabling multiple CloudWatch Cross-Account "monitoring" accounts (accounts where the dashboards are displayed)
- [ ] Mechanisms to trigger the CloudWatch Dashboard scripts.
- [ ] Lambda versions of the script(s).
