# Overview of CloudWatch Cross-Account Observability Configuration

## Terms

- _Monitoring account_ is the central account.
- _Source accounts(s)_ are the accounts the central account will access.

## Example Account Structure - Single Monitoring Account

| Account Number | Purpose    | Name                    |
| -------------- | ---------- | ----------------------- |
| 161521808930   | Monitoring | Central Observability   |
| 626190824234   | Source     | MPA and Root of AWS Org |
| 627710063647   | Source     | Websites                |
| 338557412966   | Source     | EBS testing             |
| 357044226454   | Source     | EC2 testing             |
| 579556785526   | Source     | EKS testing             |

## IAM Policy - Source Accounts

CloudWatch-CrossAccountSharingRole

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

# Example Account Structure - Single Monitoring Account

In this example, a secondary Observability Account is configured. In this case, the IAM Policy `CloudWatch-CrossAccountSharingRole` in the Source Accounts has to be updated to include the second account.

| Account Number | Purpose    | Name                    |
| -------------- | ---------- | ----------------------- |
| 161521808930   | Monitoring | Central Observability   |
| 626190824234   | Monitoring | Secondary Observability |
| 627710063647   | Source     | Websites                |
| 338557412966   | Source     | EBS testing             |
| 357044226454   | Source     | EC2 testing             |
| 579556785526   | Source     | EKS testing             |

## IAM Policy - Multiple Monitoring Accounts

CloudWatch-CrossAccountSharingRole

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
