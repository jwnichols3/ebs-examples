variable "region" {
  description = "The AWS region"
  type        = string
  default     = "us-west-2"
}
variable "profile" {
  description = "The AWS profile"
  type        = string
  default     = "default"
}

variable "schedule_rate" {
  description = "The frequency of the EventBridge schedule in minutes"
  type        = number
  default     = 1
}
variable "logging_level" {
  description = "Logging level for the Lambda function (DEBUG or INFO)"
  type        = string
  default     = "INFO"
}

provider "aws" {
  region  = var.region
  profile = var.profile
}

resource "aws_iam_role" "lambda_role" {
  name = "ebs_custom_metric_lambda_role"
  assume_role_policy = jsonencode({
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ],
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "lambda_policy"
  role   = aws_iam_role.lambda_role.id
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:PutMetricData",
        "ec2:DescribeVolumes",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_lambda_function" "ebs_lambda" {
  function_name    = "ebs_lambda_cw_custom_metric_latency"
  role             = aws_iam_role.lambda_role.arn
  handler          = "ebs-lambda-cw-custom-metric-latency.lambda_handler" # Update this with the correct handler
  runtime          = "python3.8"                                          # Update to the Python version you are using
  filename         = "ebs-lambda-cw-custom-metric-latency.zip"
  source_code_hash = filebase64sha256("ebs-lambda-cw-custom-metric-latency.zip")

  environment {
    variables = {
      PAGINATION_COUNT = 300
      TIME_INTERVAL    = var.schedule_rate * 60
      GET_BATCH_SIZE   = 500
      PUT_BATCH_SIZE   = 1000
      LOGGING_LEVEL    = var.logging_level
    }
  }

  timeout = 55 # Set the timeout based on your needs
}

resource "aws_cloudwatch_event_rule" "scheduled_rule" {
  name                = "ebs-latency-custom-metric-scheduled-rule"
  description         = "Calculates EBS Read and Write Latency for all volumes and update the corresponding custom metric in CloudWatch."
  schedule_expression = "rate(${var.schedule_rate} minute)"
}

resource "aws_cloudwatch_event_target" "invoke_lambda_scheduled" {
  rule      = aws_cloudwatch_event_rule.scheduled_rule.name
  target_id = "invoke_lambda_function"
  arn       = aws_lambda_function.ebs_lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ebs_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduled_rule.arn
}
