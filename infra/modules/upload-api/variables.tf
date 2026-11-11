variable "name" {
  description = "Name for the Lambda function, role and REST API."
  type        = string
}

variable "lambda_source_dir" {
  description = "Directory produced by scripts/build_lambda.sh (code + deps)."
  type        = string
}

variable "subnet_ids" {
  description = "Private-app subnets for the Lambda ENIs."
  type        = list(string)
}

variable "security_group_id" {
  description = "Lambda security group (allowed into the DB)."
  type        = string
}

variable "db_host" {
  description = "RDS endpoint address."
  type        = string
}

variable "db_port" {
  description = "RDS port."
  type        = number
}

variable "db_name" {
  description = "Database name."
  type        = string
}

variable "db_secret_arn" {
  description = "RDS-managed master credentials secret."
  type        = string
}

variable "raw_bucket" {
  description = "raw-uploads bucket name."
  type        = string
}

variable "cognito_user_pool_arn" {
  description = "User pool for the API Gateway authorizer."
  type        = string
}

variable "stage_name" {
  description = "API Gateway stage (CloudFront uses /<stage> as origin path)."
  type        = string
  default     = "v1"
}

variable "throttle_rate_limit" {
  description = "Stage steady-state requests per second."
  type        = number
  default     = 10
}

variable "throttle_burst_limit" {
  description = "Stage burst requests."
  type        = number
  default     = 20
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 14
}
