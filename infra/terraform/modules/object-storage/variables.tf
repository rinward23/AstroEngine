variable "cloud" {
  type = string
}

variable "environment" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "retention_days" {
  type    = number
  default = 30
}
