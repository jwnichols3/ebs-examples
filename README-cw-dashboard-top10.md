# CloudWatch Dashboard - Top 10 Read and Write Latency by EBS Volume

# Thing to Change and Consider

EBS `VolumeReadLatency` and `VolumeWriteLatency` are custom metrics calculated by a Lambda function that retrieves EBS volume metrics, calculates the two latency values, and puts the custom metrics into CloudWatch. This Laambda function runs every minute on a schedule via EventBridge Rules.

The Lambda function in this repo writes to the CW namespace "Custom_EBS". Make sure this matches the namespace the dashboard expects metrics from.

This repo has the [Terraform code example](./terraform-latency-custom-metric/) to deploy the Lambda function and schedule it. You can review it and make adjustments accordingly.

Note: this is provided as-is and is meant to be an example.

# Details of the CloudWatch Dashboard

The [example CloudWatch JSON configuration](./ebs-cw-dashboard-latency-top-10-example.json) defines a widget for an AWS CloudWatch Dashboard that displays a time-series graph related to the read latency of Amazon Elastic Block Store (EBS) volumes. Here's what each part of the configuration does:

1. **Metrics**:

   - **Expression**: The expression is using a combination of `SEARCH`, `SORT`, and `REMOVE_EMPTY` functions to find, order, and filter the metrics.
     - `SEARCH(' {Custom_EBS,VolumeId} MetricName=\"VolumeReadLatency\"', 'Average', 60)`: This part searches for the metrics that have a `MetricName` of `"VolumeReadLatency"` and are tagged with either `Custom_EBS` or `VolumeId`. It considers the average value over the last 60 seconds.
     - `SORT(..., MAX, DESC, 100)`: This sorts the search results by the maximum value in descending order and takes the top 100 results.
     - `REMOVE_EMPTY(...)`: This function removes any empty or null results from the sorted list.
   - **Label**: The label "EBS" is used to name the metric on the graph.
   - **ID**: A unique identifier for the expression within the widget.
   - **Region**: The AWS region where the metrics are pulled from. In this case, it's `"us-west-2"`.

2. **View**: Sets the type of graph. `"timeSeries"` means it will be a line chart representing the metric over time.

3. **Stacked**: This is set to `false`, meaning the graph lines will not be stacked on top of each other if there are multiple data points.

4. **Region**: The AWS region for the widget itself, also `"us-west-2"` in this case.

5. **Stat**: The statistic to be displayed, which is `"Average"` in this case. It corresponds to the average read latency.

6. **Period**: The granularity of the data points in seconds. A period of `300` means that each data point on the graph represents an average over 5 minutes.

7. **Title**: The title of the widget, `"Read Latency"`, which will be displayed at the top of the widget.

To make the Write Latency widget, copy the Read Latency Dashboard widget and change the expression to use 'VolumeWriteLatency' instead of 'VolumeReadLatency'.
