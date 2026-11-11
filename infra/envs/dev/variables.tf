variable "project" {
  description = "Project name, used in resource names and tags."
  type        = string
  default     = "mytube"
}

variable "env" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Primary AWS region."
  type        = string
  default     = "il-central-1"
}

variable "az_count" {
  description = "Number of AZs to spread subnets across."
  type        = number
  default     = 2
}

variable "nat_per_az" {
  description = "One NAT gateway per AZ (HA) instead of one shared (cheaper)."
  type        = bool
  default     = false
}

variable "db_multi_az" {
  description = "Run RDS Multi-AZ."
  type        = bool
  default     = false
}

variable "local_dev_urls" {
  description = "Extra OAuth callback/logout URLs for running the frontend locally. Set to [] to disable."
  type        = list(string)
  default     = ["http://localhost:8080/"]
}

variable "alarm_email" {
  description = "Optional email for the DLQ alarm. Null = alarm shows in CloudWatch only."
  type        = string
  default     = null
}
