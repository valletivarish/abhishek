output "output_bucket_name" {
  description = "S3 bucket name for experiment outputs"
  value       = aws_s3_bucket.output.bucket
}

output "output_bucket_arn" {
  description = "S3 bucket ARN for experiment outputs"
  value       = aws_s3_bucket.output.arn
}

output "events_function_names" {
  description = "List of events workload Lambda function names"
  value       = sort([for func in aws_lambda_function.events : func.function_name])
}

output "batch_function_names" {
  description = "List of batch workload Lambda function names"
  value       = sort([for func in aws_lambda_function.batch : func.function_name])
}

output "all_function_names" {
  description = "List of all Lambda function names"
  value       = sort(concat([for func in aws_lambda_function.events : func.function_name], [for func in aws_lambda_function.batch : func.function_name]))
}

output "total_function_count" {
  description = "Total number of Lambda functions deployed"
  value       = length(aws_lambda_function.events) + length(aws_lambda_function.batch)
}

output "events_function_count" {
  description = "Number of events workload Lambda functions"
  value       = length(aws_lambda_function.events)
}

output "batch_function_count" {
  description = "Number of batch workload Lambda functions"
  value       = length(aws_lambda_function.batch)
}

output "lambda_execution_role_arn" {
  description = "ARN of the IAM role used by Lambda functions"
  value       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.lambda_execution_role_name}"
}

output "experiment_runner_commands" {
  description = "Commands to run the experiment using the deployed functions"
  value = {
    events = "python -m runner.experiment_runner --function-prefix 'ingest-events-' --invocations 50 --trials 5 --execute-queries"
    batch  = "python -m runner.experiment_runner --function-prefix 'ingest-batch-' --invocations 20 --trials 5 --execute-queries"
  }
}

output "events_function_arns" {
  description = "List of events workload Lambda function ARNs"
  value       = sort([for func in aws_lambda_function.events : func.arn])
}

output "batch_function_arns" {
  description = "List of batch workload Lambda function ARNs"
  value       = sort([for func in aws_lambda_function.batch : func.arn])
}

output "all_function_arns" {
  description = "List of all Lambda function ARNs"
  value       = sort(concat([for func in aws_lambda_function.events : func.arn], [for func in aws_lambda_function.batch : func.arn]))
}