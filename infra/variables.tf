variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-1"
}

variable "output_bucket_name" {
  description = "Globally unique S3 bucket name for experiment outputs"
  type        = string
  default     = "lambda-s3-exp-output-CHANGE-ME"
}

variable "lambda_execution_role_name" {
  description = "Name of existing IAM role for Lambda execution (e.g., LabRole, voclabs)"
  type        = string
  default     = "LabRole"
}

variable "memory_levels_mb" {
  description = "Lambda memory levels in MB"
  type        = list(number)
  default     = [512, 1024, 2048]
}

variable "events_batch_levels" {
  description = "Number of events to batch for events workload"
  type        = list(number)
  default     = [1, 10, 100]
}

variable "event_bytes_default" {
  description = "Default size of individual events in bytes"
  type        = number
  default     = 1024
}

variable "multipart_mb_levels" {
  description = "Multipart part sizes in MB for batch workload"
  type        = list(number)
  default     = [8, 32, 64]
}

variable "object_mb_default" {
  description = "Default object size in MB for batch workload"
  type        = number
  default     = 100
}

variable "reserved_concurrency_lvls" {
  description = "Reserved concurrency levels"
  type        = list(number)
  default     = [0, 10, 50]
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "experiment"
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "lambda-s3-exp"
}