variable "name" {
  description = "Name prefix for the ALB, ASG, role and log group."
  type        = string
}

variable "vpc_id" {
  description = "VPC for the target group."
  type        = string
}

variable "subnet_ids" {
  description = "Private-app subnets for the internal ALB and the instances."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group for the ALB."
  type        = string
}

variable "instance_security_group_id" {
  description = "Security group for backend instances."
  type        = string
}

variable "alb_port" {
  description = "ALB listener port."
  type        = number
  default     = 80
}

variable "app_port" {
  description = "Container port."
  type        = number
  default     = 8000
}

variable "origin_verify_secret" {
  description = "Value CloudFront must send in X-Origin-Verify; anything else gets 403."
  type        = string
  sensitive   = true
}

variable "ecr_repository_url" {
  description = "Backend image repository URL."
  type        = string
}

variable "ecr_repository_arn" {
  description = "Backend image repository ARN (for pull permissions)."
  type        = string
}

variable "image_tag" {
  description = "Image tag to run. Changing it rolls the ASG."
  type        = string
  default     = "latest"
}

variable "db_secret_arn" {
  description = "RDS-managed master credentials secret."
  type        = string
}

variable "raw_bucket" {
  description = "raw-uploads bucket name."
  type        = string
}

variable "processed_bucket" {
  description = "processed-videos bucket name."
  type        = string
}

variable "container_env" {
  description = "Non-secret environment variables for the container."
  type        = map(string)
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.small"
}

variable "min_size" {
  description = "Minimum instances."
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum instances."
  type        = number
  default     = 4
}

variable "target_requests_per_instance" {
  description = "Target-tracking value for ALBRequestCountPerTarget (requests per minute per instance)."
  type        = number
  default     = 500
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 14
}
