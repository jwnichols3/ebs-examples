# Overview of CloudWatch Cross-Account Observability Access Manager (OAM)

This document describes some of the nuances to setting up cross-account and cross-region CloudWatch Observability (known as Observability Access Manager, OAM) using the [Setup Instructions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Cross-Account-Cross-Region.html). The setup is done using ClickOps unless time and effort is invested in setting up SSM Automation.

## To Do Tracking

[Cross Account OAM Setup To Do Tracking](./TODO.md)

## Terraform Modules Related to OAM

[Github Information from AWS](https://github.com/aws-samples/cloudwatch-obervability-access-manager-terraform)

#### Resources

- [OAM Links](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_link)
- [OAM Sink](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_sink)
- [OAM Sink Link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_sink_link)

#### Data Sources

- [OAM Link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_link)
- [OAM Links](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_links)
- [OAM Sink](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_sink)
- [OAM Sinks](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_sinks)

## Terms

- _Monitoring account_ is the central account.
- _Source accounts(s)_ are the accounts the central account will access.

## Example Account Structure - Single Monitoring Account

| Account Number | Purpose    | Name                    |
| -------------- | ---------- | ----------------------- |
| 161521808930   | Monitoring | Central Observability   |
| 626190824234   | Source     | MPA and Root of AWS Org |
| 627710063647   | Source     | Websites                |
| 338557412966   | Source     | EBS-HME testing         |
| 357044226454   | Source     | EC2 testing             |
| 579556785526   | Source     | EKS testing             |

Here are some other ways the account lists are needed during the ClickOps setup:

```text
626190824234, 627710063647, 338557412966, 357044226454, 579556785526
```

```text
626190824234 Root
627710063647 Websites
338557412966 EBS-HME
357044226454 EC2
579556785526 EKS
```

### IAM Policy - Source Accounts

The IAM Policy `CloudWatch-CrossAccountSharingRole` in each of the Source Accounts has the `sts:AssumeRole` Trust Relationship. Note the Account Number in the `Principal` is the "Monitoring" account above.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::161521808930:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Example Account Structure - Single Monitoring Account

In this example, a secondary Observability Account is configured. In this case, the IAM Policy `CloudWatch-CrossAccountSharingRole` in the Source Accounts has to be updated to include the second account.

| Account Number | Purpose    | Name                    |
| -------------- | ---------- | ----------------------- |
| 161521808930   | Monitoring | Central Observability   |
| 626190824234   | Monitoring | Secondary Observability |
| 627710063647   | Source     | Websites                |
| 338557412966   | Source     | EBS testing             |
| 357044226454   | Source     | EC2 testing             |
| 579556785526   | Source     | EKS testing             |

### IAM Policy - Multiple Monitoring Accounts

The IAM Policy `CloudWatch-CrossAccountSharingRole` in each of the Source Accounts has the `sts:AssumeRole` Trust Relationship. Note there are `Principal` entries for each of the "Monitoring" account above.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::626190824234:root",
          "arn:aws:iam::161521808930:root"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
