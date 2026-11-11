variable "name" {
  description = "Name prefix (also used for the Hosted UI domain prefix)."
  type        = string
}

variable "callback_urls" {
  description = "Allowed OAuth redirect URLs (site URL; http://localhost only for local testing)."
  type        = list(string)
}

variable "logout_urls" {
  description = "Allowed sign-out redirect URLs."
  type        = list(string)
}

variable "deletion_protection" {
  description = "Protect the user pool from deletion."
  type        = bool
  default     = false
}
