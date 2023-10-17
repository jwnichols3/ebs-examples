import boto3
from tabulate import tabulate

# Initialize EC2 client
ec2_client = boto3.client("ec2")

# Fetch all EC2 instances
response = ec2_client.describe_instances()

# Initialize empty list to store instance details
instance_details = []

# Loop through reservations and instances
for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:
        instance_id = instance["InstanceId"]
        key_name = instance.get(
            "KeyName", "N/A"
        )  # Get Key Pair name if available, else set to 'N/A'
        public_ip = instance.get(
            "PublicIpAddress", "N/A"
        )  # Get Public IP if available, else set to 'N/A'
        if public_ip != "N/A":
            ssh_command = f"ssh -i ~/.ssh/{key_name}.pem ec2-user@{public_ip}"

        # Extract EC2 name from tags
        ec2_name = "N/A"
        if "Tags" in instance:
            for tag in instance["Tags"]:
                if tag["Key"] == "Name":
                    ec2_name = tag["Value"]
                    break

        # Append details to list
        instance_details.append(
            [instance_id, ec2_name, key_name, public_ip, ssh_command]
        )


headers = ["Instance ID", "Name", "Key Pair", "Public IP", "SSH"]

# Display the instance details
print(tabulate(instance_details, headers, tablefmt="grid"))
