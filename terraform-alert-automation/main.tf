provider "aws" {
  region  = "us-west-2"
  profile = "hme"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricAlarm",
          "sns:Publish"
        ],
        Resource = "*"
      }
    ]
  })
}

# SNS topic
resource "aws_sns_topic" "ebs_alarms" {
  name = "ebs_alarms"
}

# SNS topic subscription
resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.ebs_alarms.arn
  protocol  = "email"
  endpoint  = "example@example.com"
}

# Lambda function
resource "aws_lambda_function" "ebs_alarm_lambda" {
  filename      = "ebs-lambda-cw-alarm-impairedvol-create.zip"
  function_name = "ebs_alarm_lambda"
  role          = aws_iam_role.lambda_role.arn
  handler       = "ebs-lambda-cw-alarm-impairedvol-create.lambda_handler"
  runtime       = "python3.8"

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.ebs_alarms.arn
    }
  }
}

# CloudWatch event rule
resource "aws_cloudwatch_event_rule" "ebs_creation_rule" {
  name        = "ebs-volume-alert-creation"
  description = "Trigger when an EBS volume is created"

  event_pattern = <<PATTERN
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["CreateVolume"]
  }
}
PATTERN
}

# CloudWatch event target
resource "aws_cloudwatch_event_target" "ebs_creation_target" {
  rule      = aws_cloudwatch_event_rule.ebs_creation_rule.name
  target_id = "EBSVolumeCreation"
  arn       = aws_lambda_function.ebs_alarm_lambda.arn
}

# Permission for CloudWatch to invoke Lambda
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ebs_alarm_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ebs_creation_rule.arn
}
