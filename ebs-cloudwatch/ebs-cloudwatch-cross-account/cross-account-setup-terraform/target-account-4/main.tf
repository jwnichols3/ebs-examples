provider "aws" {
  region = "us-west-2"
  # Configure your target AWS account here
}

# IAM Role to be assumed
resource "aws_iam_role" "cross_account_role" {
  name = "CrossAccountObservabilityRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${var.main_account_id}:root"
        }
      }
    ]
  })
}

# IAM Policy for EC2, EBS, and CloudWatch Metrics
resource "aws_iam_role_policy" "cross_account_policy" {
  name = "CrossAccountPolicy"
  role = aws_iam_role.cross_account_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = ["ec2:Describe*", "ebs:Describe*", "cloudwatch:GetMetricData", "cloudwatch:ListMetrics"],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}
