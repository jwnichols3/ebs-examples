# TODO

This is where CloudWatch-centric examples are for EBS Volumes. These are the aspects:

- CloudWatch Alarms
- CloudWatch Custom Metrics
- CloudWatch Dashboards
- CLI output

## CloudWatch Alarms

On Oct 20, 2023 the `ebs-cw-alarm-manager.py` script replaced the `impairedvol` and `latency` scripts.

### `ebs-cw-alarm-manager.py`

- cross-region awareness (e.g. CloudWatch Dashboard in one region, EBS / EC2 instances in a different region)
- Adding tests
- Abstraction so that additional alarms can be added

## CloudWatch Custom Metrics

### `ebs-cw-custom-metric-latency-batch`

-

### `ebs-cw-custom-metric-latency.py`

-

## CloudWatch Dashboards

### `ebs-cw-dashboards-by-tag.py`

-

### `ebs-cw-dashboard-impairedvol.py`

-

### `ebs-cw-dashboard-latency.py`

### `ebs-cw-dashboard-manager.py`

- Converge on the `manager` script as a way to implement impairedvol and latency (similar to how alarms are a single script)
- Cross-region awareness

## CloudWatch CLI

### `ebs-cw-show-detailed-metrics-for-latency.py`

-

### `ebs-cw-show-impairedvol.py`

-

### `ebs-cw-show-latency-metrics-current.py`

-
