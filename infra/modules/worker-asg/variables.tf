variable "name" {
  description = "Name prefix for the queues, ASG, role and log group."
  type        = string
}

variable "subnet_ids" {
  description = "Private-app subnets for worker instances."
  type        = list(string)
}

variable "instance_security_group_id" {
  description = "Worker security group (no inbound)."
  type        = string
}

variable "ecr_repository_url" {
  description = "Worker image repository URL."
  type        = string
}

variable "ecr_repository_arn" {
  description = "Worker image repository ARN (for pull permissions)."
  type        = string
}

variable "image_tag" {
  description = "Image tag to run."
  type        = string
  default     = "latest"
}

variable "db_secret_arn" {
  description = "RDS-managed master credentials secret."
  type        = string
}

variable "raw_bucket" {
  description = "raw-uploads bucket name (event source, read access)."
  type        = string
}

variable "processed_bucket" {
  description = "processed-videos bucket name (HLS output)."
  type        = string
}

variable "container_env" {
  description = "Non-secret environment variables for the container (QUEUE_URL and ASG_NAME are added)."
  type        = map(string)
}

variable "instance_type" {
  description = "EC2 instance type. ffmpeg is CPU-bound; t3 runs in unlimited-credit mode by default."
  type        = string
  default     = "t3.medium"
}

variable "volume_size_gb" {
  description = "Root EBS size; must hold the largest upload plus its HLS output."
  type        = number
  default     = 40
}

variable "min_size" {
  description = "Minimum workers."
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum workers."
  type        = number
  default     = 3
}

variable "target_backlog_per_instance" {
  description = "Target visible messages per in-service worker."
  type        = number
  default     = 1
}

variable "visibility_timeout_seconds" {
  description = "Initial SQS visibility timeout. Workers extend it while ffmpeg runs (heartbeat)."
  type        = number
  default     = 1800
}

variable "alarm_email" {
  description = "Optional email for the DLQ alarm (confirm the SNS subscription email). Null = alarm without notification."
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 14
}
