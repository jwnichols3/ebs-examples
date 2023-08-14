# STATUS OF SCRIPT:

IN PROGRESS as of 8/14

# AWS Systems Manager Automation - EBS

# ebs-ssm-cw-alarm-create.yaml

## Overview of `ebs-ssm-cw-alarm-create.yaml`

This script creates a CloudWatch alarm named "ImpairedVol\_" followed by the Volume ID for all EBS volumes in your AWS account. The alarm is triggered if `(VolumeReadOps + VolumeWriteOps) = 0 and VolumeQueueLength > 0` for 5 minutes.

# Features

- Automatically lists all the EBS volumes in the account.
- Creates a CloudWatch alarm for each volume based on the defined metric.
- Utilizes AWS Systems Manager (SSM) to automate the process.

# Requirements

- AWS CLI or SDK properly configured.
- Appropriate IAM permissions (detailed below).
- IAM Permissions
- The following IAM permissions are required to execute this script:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2Permissions",
      "Effect": "Allow",
      "Action": ["ec2:DescribeVolumes"],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SSMPermissions",
      "Effect": "Allow",
      "Action": [
        "ssm:CreateDocument",
        "ssm:DeleteDocument",
        "ssm:DescribeDocument",
        "ssm:UpdateDocument",
        "ssm:ExecuteAutomation"
      ],
      "Resource": "*"
    }
  ]
}
```

# Usage

1. Upload the YAML document to AWS Systems Manager (SSM) as an SSM Automation document.
2. Execute the SSM Automation, either manually through the AWS Management Console or programmatically through the AWS CLI/SDK.

# SNS Topic

The script references an SNS topic with the ARN `arn:aws:sns:us-west-2:338557412966:ebs_alarms. Adjust this to reflect your SNS topic. Make sure the topic is properly configured to receive notifications for the alarms.

# Note

Make sure to thoroughly test this script in a non-production environment before using it in a production setting. Always ensure that IAM permissions are configured according to the principle of least privilege.
