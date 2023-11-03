variable "ec2_key_pair" {
  description = "The name of the EC2 Key Pair"
  type        = string
  default     = "jnicamzn-ec2-uswest2" # This is an optional default value.
}

variable "aws_region" {
  description = "The AWS Region"
  type        = string
  default     = "us-west-2" # This is an optional default value.
}

variable "lambda_zip_path" {
  description = "The path to the lambda zip file"
  type        = string
  // You can provide a default value or leave it out if you prefer to always pass the value explicitly
  default = "../../vpc-endpoints-check-lambda.zip"
}

provider "aws" {
  region = var.aws_region # Change this to your desired AWS region
}

data "aws_availability_zones" "available" {}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "main_vpc"
  }
}

resource "aws_subnet" "public_subnet" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = element(flatten([for az in data.aws_availability_zones.available.names : tolist([az])]), count.index)
  map_public_ip_on_launch = true

  tags = {
    Name = "public_subnet-${count.index}"
  }
}

resource "aws_subnet" "private_subnet" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 3}.0/24"
  availability_zone = element(flatten([for az in data.aws_availability_zones.available.names : tolist([az])]), count.index)

  tags = {
    Name = "private_subnet-${count.index}"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public_subnet[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "remote_access" {
  name        = "remote_access"
  description = "SG for remote access to bastion host"
  vpc_id      = aws_vpc.main.id

  # SSH access for specific IPs
  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"
    cidr_blocks = [
      "198.134.98.50/32", # Mobile
      "69.42.19.106/32"   # Home
    ]
  }

  # RDP access for specific IPs
  ingress {
    from_port = 3389
    to_port   = 3389
    protocol  = "tcp"
    cidr_blocks = [
      "198.134.98.50/32", # Mobile
      "69.42.19.106/32"   # Home
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Allow all outbound traffic
  }

  tags = {
    Name = "remote_access"
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["amazon"] # Amazon is the owner of Amazon Linux AMI
}

resource "aws_security_group" "vpc_endpoint_sg" {
  name        = "vpc-endpoint-sg"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "vpc-endpoint-sg"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id          = aws_vpc.main.id
  service_name    = "com.amazonaws.${var.aws_region}.s3"
  route_table_ids = [aws_route_table.public.id, aws_route_table.private.id]
}

resource "aws_vpc_endpoint" "ec2" {
  vpc_id             = aws_vpc.main.id
  service_name       = "com.amazonaws.${var.aws_region}.ec2"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private_subnet.*.id
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
}

resource "aws_vpc_endpoint" "sns" {
  vpc_id             = aws_vpc.main.id
  service_name       = "com.amazonaws.${var.aws_region}.sns"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private_subnet.*.id
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
}

resource "aws_vpc_endpoint" "cloudwatch" {
  vpc_id             = aws_vpc.main.id
  service_name       = "com.amazonaws.${var.aws_region}.monitoring"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private_subnet.*.id
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public_subnet[0].id
  key_name               = var.ec2_key_pair
  vpc_security_group_ids = [aws_security_group.remote_access.id]

  tags = {
    Name = "bastion_host"
  }
}

resource "aws_iam_policy" "vpc_endpoint_policy" {
  name        = "VpcEndpointAccessPolicy"
  description = "Policy to allow access to AWS services via VPC Endpoints"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = "*",
        Resource = "*",
        Effect   = "Allow",
        Sid      = "VpcEndpointAccess"
      }
    ]
  })
}

resource "aws_security_group" "public_egress" {
  vpc_id = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "public_egress_sg"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_subnet[0].id

  tags = {
    Name = "main_nat_gateway"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private_subnet[count.index].id
  route_table_id = aws_route_table.private.id
}

# IAM role for the Lambda function
resource "aws_iam_role" "lambda_execution" {
  name = "lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
    }]
  })
}

# Attach the IAM policy to the IAM role
resource "aws_iam_role_policy_attachment" "vpc_endpoint_policy_attachment" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.vpc_endpoint_policy.arn
}

resource "aws_lambda_function" "vpc_endpoints_check" {
  function_name = "vpc_endpoints_check_lambda"
  handler       = "vpc-endpoints-check-lambda.lambda_handler"
  role          = aws_iam_role.lambda_execution.arn
  runtime       = "python3.11"

  s3_bucket = aws_s3_bucket.lambda_code.bucket
  s3_key    = aws_s3_object.lambda_code_object.key


  memory_size = 256 # Set the Lambda function's memory to 256 MB
  timeout     = 180 # Set the Lambda function's timeout to 3 minutes (180 seconds)

  # Subnet and Security Group Configuration
  vpc_config {
    subnet_ids         = aws_subnet.private_subnet[*].id
    security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
  }

  # Optional: Set environment variables if needed
  environment {
    variables = {
      // add environment variables here
    }
  }
}

# CloudWatch Logs group for Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.vpc_endpoints_check.function_name}"
  retention_in_days = 14
}

# Allow the Lambda function to be invoked from the VPC
resource "aws_lambda_permission" "allow_vpc" {
  statement_id  = "AllowExecutionFromVPC"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.vpc_endpoints_check.function_name
  principal     = "ec2.amazonaws.com"

  source_arn = aws_vpc.main.arn
}

resource "aws_iam_policy" "lambda_s3_access" {
  name        = "LambdaS3AccessPolicy"
  description = "IAM policy for lambda to access S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
        ],
        Resource = [
          "${aws_s3_bucket.lambda_code.arn}/*", # Grants access to objects within the bucket
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attachment" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

resource "aws_s3_bucket" "lambda_code" {
  bucket = "jnicamzn-ec2-lambda-code-bucket-usw2-${random_string.suffix.result}"
  tags = {
    Name = "jnicamzn-ec2 us-west-2 Lambda Code Bucket"
  }
}

resource "aws_s3_object" "lambda_code_object" {
  bucket = aws_s3_bucket.lambda_code.bucket
  key    = "vpc-endpoints-check-lambda.zip"
  source = var.lambda_zip_path
  etag   = filemd5(var.lambda_zip_path)
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}
