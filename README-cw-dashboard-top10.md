# CloudWatch Dashboard - Top 10 Read and Write Latency by EBS Volume

## Thing to Change and Consider

EBS `VolumeReadLatency` and `VolumeWriteLatency` are custom metrics calculated by a Lambda function that retrieves EBS volume metrics, calculates the two latency values, and puts the custom metrics into CloudWatch. This Laambda function runs every minute on a schedule via EventBridge Rules.

The Lambda function in this repo writes to the CW namespace "Custom_EBS". Make sure this matches the namespace the dashboard expects metrics from.

This repo has the [Terraform code example](./terraform-latency-custom-metric/) to deploy the Lambda function and schedule it. You can review it and make adjustments accordingly.

Note: this is provided as-is and is meant to be an example.

## Details of the CloudWatch Dashboard

The [example CloudWatch JSON configuration](./ebs-cw-dashboard-latency-top-10-example.json) defines a widget for an AWS CloudWatch Dashboard that displays a time-series graph related to the read latency of Amazon Elastic Block Store (EBS) volumes. Here's what each part of the configuration does:

### Dashboard Configuration

- **View**: Time Series
- **Stacked**: False
- **Region**: us-west-2
- **Statistical Method**: Average
- **Period**: 60 seconds
- **Title**: Read Latency

#### Metrics

- **Expression**: `SELECT MAX(VolumeReadLatency) FROM Custom_EBS GROUP BY VolumeId ORDER BY MAX() DESC LIMIT 10`
  - **Label**: EBS
  - **ID**: e1
  - **Region**: us-west-2
  - **Period**: 60 seconds

## JSON Definition

```json
{
  "metrics": [
    [
      {
        "expression": "SELECT MAX(VolumeReadLatency) FROM Custom_EBS GROUP BY VolumeId ORDER BY MAX() DESC LIMIT 10",
        "label": "EBS",
        "id": "e1",
        "region": "us-west-2",
        "period": 60
      }
    ]
  ],
  "view": "timeSeries",
  "stacked": false,
  "region": "us-west-2",
  "stat": "Average",
  "period": 60,
  "title": "Read Latency"
}
```

### Usage

You can create this dashboard by copying the JSON definition into the CloudWatch console, or by using the AWS SDK or CLI to create the dashboard programmatically.
