provider "aws" {
  region  = "us-west-2"
  profile = "hme"
}

# Create SNS Topic
resource "aws_sns_topic" "ebs_alarms" {
  name = "ebs_alarms"
}

# IAM Role for Lambda Function
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

# IAM Policy for Lambda Function
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
        ],
        Resource = "*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "ebs_alarm_lambda" {
  filename         = "ebs-lambda-cw-alarm-impairedvol-create.zip"
  function_name    = "ebs_alarm_lambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "ebs-lambda-cw-alarm-impairedvol-create.lambda_handler"
  source_code_hash = filebase64sha256("ebs-lambda-cw-alarm-impairedvol-create.zip")
  runtime          = "python3.8"

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.ebs_alarms.arn
    }
  }
}

# EventBridge Rule for EBS Volume Creation
resource "aws_cloudwatch_event_rule" "ebs_creation_rule" {
  name        = "ebs-volume-creation"
  description = "EBS Volume Creation"

  event_pattern = jsonencode({
    "source" : ["aws.ec2"],
    "detail-type" : ["AWS API Call via CloudTrail"],
    "detail" : {
      "eventName" : ["CreateVolume"]
    }
  })
}

# Event Target to Invoke Lambda
resource "aws_cloudwatch_event_target" "ebs_creation_target" {
  rule      = aws_cloudwatch_event_rule.ebs_creation_rule.name
  target_id = "EBSVolumeCreation"
  arn       = aws_lambda_function.ebs_alarm_lambda.arn
}

# Lambda Permission to Allow EventBridge to Invoke Function
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ebs_alarm_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ebs_creation_rule.arn
}

# SNS Topic Subscription (Optional: Add subscriptions as needed)
resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.ebs_alarms.arn
  protocol  = "email"
  endpoint  = "jnicamzn+sns-ebs@amazon.com"
}
