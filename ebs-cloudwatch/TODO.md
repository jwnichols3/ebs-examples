# TODO

This is where CloudWatch-centric examples are for EBS Volumes. These are the aspects:

- CloudWatch Alarms
- CloudWatch Custom Metrics
- CloudWatch Dashboards
- CLI output

## CloudWatch Alarms

On Oct 20, 2023 the `ebs-cw-alarm-manager.py` script replaced the `impairedvol` and `latency` scripts.

### `ebs-cw-alarm-manager.py`

- [ ] cross-region awareness (e.g. CloudWatch Dashboard in one region, EBS / EC2 instances in a different region)
- [ ] Adding tests
- [ ] Abstraction so that additional alarms can be added without lots of code duplication.
- [ ] Configuration file for options versus the CONSTANTS.

## CloudWatch Custom Metrics

These scripts create custom metrics for EBS volumes in two ways - a volume-by-volume way and using batch calls to CloudWatch. Part of the exercise is to show the speed difference between the two approaches.

### `ebs-cw-custom-metric-latency-batch`

-

### `ebs-cw-custom-metric-latency.py`

-

## CloudWatch Dashboards

### `ebs-cw-dashboards-by-tag.py`

### `ebs-cw-dashboards-volumestatus.py`

This is a good cross-region aware dashboard that displays volume status. It has sharding awareness and `--tag` support.

- [ ] Error checking and exception handling.
- [ ] Make this the foundation for the `manager` script.
- [ ] Change from print statements to logging.

### `ebs-cw-dashboard-impairedvol.py`

- [ ] Migrate this to the `manager` script approach for consistency.

### `ebs-cw-dashboard-latency.py`

- [ ] Migrate this to the `manager` script approach for consistency.

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
