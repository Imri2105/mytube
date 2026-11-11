variable "name" {
  description = "Name prefix for buckets (account ID is appended for uniqueness)."
  type        = string
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete non-empty buckets. Convenient for dev."
  type        = bool
  default     = false
}

variable "upload_allowed_origins" {
  description = "Origins allowed to PUT to raw-uploads via presigned URLs (the site URL). Empty = no CORS rule yet."
  type        = list(string)
  default     = []
}

variable "cloudfront_distribution_arn" {
  description = "Distribution allowed to read processed-videos and frontend-static via OAC. Null until the edge exists."
  type        = string
  default     = null
}
