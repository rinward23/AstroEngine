variable "cloud" {
  type        = string
  description = "Cloud provider identifier."
}

variable "environment" {
  type        = string
}

variable "db_name" {
  type        = string
}

variable "db_version" {
  type        = string
  default     = "15"
}

variable "instance_class" {
  type        = string
}

variable "storage_gb" {
  type        = number
  default     = 256
}

variable "subnet_ids" {
  type        = list(string)
}

variable "backup_bucket" {
  type        = string
  description = "Object storage bucket for logical backups."
}

variable "tags" {
  type    = map(string)
  default = {}
}
