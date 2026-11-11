variable "name" {
  description = "Name prefix for resources."
  type        = string
}

variable "cidr" {
  description = "VPC CIDR (/16 recommended); each subnet takes 4 more prefix bits (/20 for a /16)."
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Number of AZs (2-4)."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 4
    error_message = "az_count must be between 2 and 4."
  }
}

variable "nat_per_az" {
  description = "One NAT gateway per AZ (HA) instead of a single shared one (cheaper)."
  type        = bool
  default     = false
}

variable "alb_port" {
  description = "ALB listener port (CloudFront VPC origin -> ALB)."
  type        = number
  default     = 80
}

variable "app_port" {
  description = "Backend container port."
  type        = number
  default     = 8000
}
