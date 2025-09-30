variable "cloud" {
  type = string
}

variable "environment" {
  type = string
}

variable "alert_endpoints" {
  description = "Alert notification targets (Slack webhooks, email)."
  type        = map(string)
  default     = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
