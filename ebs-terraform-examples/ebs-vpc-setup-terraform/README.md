# Terraform VPC Infrastructure

This Terraform configuration sets up a VPC and related resources on AWS, including VPC endpoints for EC2, SNS, and CloudWatch. The Lambda script verifies connectivity to the endpoints.

## Resources Created

- VPC with public and private subnets across two availability zones
- Internet gateway and route tables for public subnet
- NAT gateway and route table for private subnet
- Security groups for SSH access and VPC endpoints
- VPC endpoints for S3, EC2, SNS, and CloudWatch
- EC2 instance in public subnet for bastion host
- IAM policy to allow access to VPC endpoints
- Lambda Script with associated IAM Policies that test the VPC endpoints

## Usage

1. Configure AWS provider and remote state backend
2. Define input variables for resources
3. Initialize and apply Terraform

## Inputs

- `aws_region` - AWS region to deploy resources
- `ec2_key_pair` - Key pair name for EC2 instance
- `lambda_zip_path` - Path to Lambda function zip file
- `allowed_ingress_cidrs` - List of CIDR blocks allowed SSH (or RDP) access to bastion host

## Outputs

- `vpc_id` - ID of the created VPC
- `public_subnet_ids` - IDs of the public subnets
- `private_subnet_ids` - IDs of the private subnets
- `bastion_ip` - Public IP of bastion host

## Notes

The VPC endpoints allow private instances to access certain AWS services without an internet gateway.
The bastion host allows inbound SSH access to the private subnet.
IAM policy grants permission to use the VPC endpoints.

Adjust resources and variables as needed for your environment.
