variable "name" {
  description = "DB identifier / name prefix."
  type        = string
}

variable "subnet_ids" {
  description = "Private-db subnet IDs."
  type        = list(string)
}

variable "security_group_id" {
  description = "DB security group."
  type        = string
}

variable "engine_version" {
  description = "PostgreSQL major version; RDS picks the latest minor and upgrades it automatically."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "multi_az" {
  description = "Standby in a second AZ."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention in days."
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "Block deletion of the instance."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot on destroy (dev convenience)."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Retention for the RDS PostgreSQL log group."
  type        = number
  default     = 14
}
