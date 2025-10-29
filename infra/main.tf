terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

provider "aws" {
  region = var.region
}

# Get current AWS account ID for role ARN construction
data "aws_caller_identity" "current" {}

# AWS Lambda Insights layer ARN for eu-west-1
# Using the standard ARN format for Lambda Insights
locals {
  lambda_insights_layer_arn = "arn:aws:lambda:${var.region}:580247275435:layer:LambdaInsightsExtension:27"
}

# Package Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../lambda_app"
  output_path = "../package.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache"]
}

# S3 bucket for experiment outputs
resource "aws_s3_bucket" "output" {
  bucket = var.output_bucket_name
  force_destroy = true
  
  tags = {
    project = var.project_name
    workload = "both"
    env     = var.environment
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "output_versioning" {
  bucket = aws_s3_bucket.output.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "output_encryption" {
  bucket = aws_s3_bucket.output.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Local values for factorial design matrices
locals {
  # Events workload: memory × batch_events × reserved_concurrency
  events_matrix = setproduct(var.memory_levels_mb, var.events_batch_levels, var.reserved_concurrency_lvls)
  events_map = {
    for combo in local.events_matrix : "${combo[0]}-${combo[1]}-${combo[2]}" => {
      memory = combo[0]
      batch  = combo[1]
      rc     = combo[2]
    }
  }
  
  # Batch workload: memory × multipart_mb × reserved_concurrency
  batch_matrix = setproduct(var.memory_levels_mb, var.multipart_mb_levels, var.reserved_concurrency_lvls)
  batch_map = {
    for combo in local.batch_matrix : "${combo[0]}-${combo[1]}-${combo[2]}" => {
      memory = combo[0]
      part   = combo[1]
      rc     = combo[2]
    }
  }
}

# Events workload Lambda functions (27 functions)
resource "aws_lambda_function" "events" {
  for_each = local.events_map

  function_name = "ingest-events-m${each.value.memory}-b${each.value.batch}-rc${each.value.rc}"
  runtime       = "python3.11"
  handler       = "handler.handler"
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  role = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.lambda_execution_role_name}"
  
  memory_size = each.value.memory
  timeout     = 300
  
  reserved_concurrent_executions = each.value.rc > 0 ? each.value.rc : null

  # Add Lambda Insights layer for enhanced metrics
  layers = [local.lambda_insights_layer_arn]

  environment {
    variables = {
      WORKLOAD           = "events"
      OUTPUT_BUCKET      = aws_s3_bucket.output.bucket
      BATCH_EVENTS       = each.value.batch
      EVENT_BYTES        = var.event_bytes_default
      MEMORY_MB          = each.value.memory
      RESERVED_CONCURRENCY = each.value.rc
      OBJECT_MB          = var.object_mb_default
      MULTIPART_MB       = 8
    }
  }

  tags = {
    project      = var.project_name
    workload     = "events"
    memory       = tostring(each.value.memory)
    batch_or_part = tostring(each.value.batch)
    rc           = tostring(each.value.rc)
    env          = var.environment
  }
}

# CloudWatch log group for events functions
resource "aws_cloudwatch_log_group" "events" {
  for_each = local.events_map

  name              = "/aws/lambda/${aws_lambda_function.events[each.key].function_name}"
  retention_in_days = 7

  tags = {
    project = var.project_name
    workload = "events"
    env     = var.environment
  }
}

# Batch workload Lambda functions (27 functions) - DEPENDS ON EVENTS COMPLETION
resource "aws_lambda_function" "batch" {
  for_each = local.batch_map

  function_name = "ingest-batch-m${each.value.memory}-p${each.value.part}-rc${each.value.rc}"
  runtime       = "python3.11"
  handler       = "handler.handler"
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  role = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.lambda_execution_role_name}"
  
  memory_size = each.value.memory
  timeout     = 900  # 15 minutes for large uploads
  
  reserved_concurrent_executions = each.value.rc > 0 ? each.value.rc : null

  # Add Lambda Insights layer for enhanced metrics
  layers = [local.lambda_insights_layer_arn]

  # Wait for ALL events functions to complete before creating batch functions
  depends_on = [aws_lambda_function.events]

  environment {
    variables = {
      WORKLOAD           = "batch"
      OUTPUT_BUCKET      = aws_s3_bucket.output.bucket
      MULTIPART_MB       = each.value.part
      OBJECT_MB          = var.object_mb_default
      MEMORY_MB          = each.value.memory
      RESERVED_CONCURRENCY = each.value.rc
      BATCH_EVENTS       = 1
      EVENT_BYTES        = var.event_bytes_default
    }
  }

  tags = {
    project      = var.project_name
    workload     = "batch"
    memory       = tostring(each.value.memory)
    batch_or_part = tostring(each.value.part)
    rc           = tostring(each.value.rc)
    env          = var.environment
  }
}

# CloudWatch log group for batch functions - DEPENDS ON BATCH FUNCTIONS
resource "aws_cloudwatch_log_group" "batch" {
  for_each = local.batch_map

  name              = "/aws/lambda/${aws_lambda_function.batch[each.key].function_name}"
  retention_in_days = 7

  tags = {
    project = var.project_name
    workload = "batch"
    env     = var.environment
  }
}