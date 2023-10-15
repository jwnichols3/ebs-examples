# AWS EC2 Launch and Management Script

## Description

This Python script automates the launching of AWS EC2 instances with attached EBS volumes. It can also list unique launch runs and terminate instances based on a launch run ID. Each launch of instances will tag the EC2 instances with a 'clustername' tag containing the provided clustername value and a LaunchRun tag that provides a unique ID.

## TODO and Feature Tracking

[To do and Feature Tracking](./TODO.md)

## Features

- Launch EC2 instances with EBS volumes
- Terminate instances by launch run ID
- List unique launch runs across all available regions
- Prompt for required AWS configurations if not provided via command line arguments

## Requirements

- Python 3.x
- Boto3
- Tabulate
- AWS CLI configured with appropriate permissions

## Installation

1. Install the required Python packages:

   ```bash
   pip install boto3 tabulate
   ```

2. Clone this repository:

   ```bash
   git clone <repository_url>
   ```

3. Navigate to the directory containing the script.

## Usage

### Launch EC2 Instances

```bash
python script_name.py --instances 2 --volumes 2 --region us-east-1 --vpc vpc-12345678 --az us-east-1a --key my-key --sg sg-12345678 --clustername my-cluster
```

### Terminate EC2 Instances

```bash
python script_name.py --terminate <LaunchRun_ID> --region us-east-1
```

### List Unique Launch Runs

```bash
python script_name.py --launchrun-list
```

## Arguments

- `--instances`: Number of EC2 instances to launch
- `--volumes`: Number of EBS volumes per instance
- `--region`: AWS region
- `--vpc`: VPC ID
- `--vol-type`: Volume Type (gp2, gp3, st1, sc1, io2)
- `--az`: AWS availability zone
- `--key`: EC2 key pair name
- `--sg`: Security group ID
- `--clustername`: Cluster name tag
- `--style`: Table style for tabulate
- `--terminate`: Terminate instances by LaunchRun ID
- `--launchrun-list`: List all unique LaunchRun IDs
- `--quiet`: Only output the LaunchRun value if successful
- `--verbose`: Print out all existing statements
- `--debug`: Output debug information
- `--no-wait`: Do not wait for instances to terminate
