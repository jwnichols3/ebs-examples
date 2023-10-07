provider "aws" {
  region = "us-west-2"
  # Configure your main AWS account here
}

# IAM Policy for CloudWatch Dashboard Read/Write
resource "aws_iam_policy" "cloudwatch_dashboard_policy" {
  name        = "CloudWatchDashboardPolicy"
  description = "Policy for CloudWatch Dashboard Read/Write"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = ["cloudwatch:PutDashboard", "cloudwatch:GetDashboard", "cloudwatch:ListDashboards", "cloudwatch:DeleteDashboards"],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

# IAM Role for the main account
resource "aws_iam_role" "main_account_role" {
  name = "MainObservabilityRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          AWS = [for id in var.target_account_ids : "arn:aws:iam::${id}:root"]
        }
      }
    ]
  })
}

# Attach the CloudWatch policy to the main account role
resource "aws_iam_role_policy_attachment" "main_account_role_cloudwatch_attachment" {
  role       = aws_iam_role.main_account_role.name
  policy_arn = aws_iam_policy.cloudwatch_dashboard_policy.arn
}
