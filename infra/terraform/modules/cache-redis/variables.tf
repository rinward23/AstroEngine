variable "cloud" {
  type = string
}

variable "environment" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "instance_class" {
  type = string
  description = "Instance size or tier for Redis."
}

variable "tags" {
  type    = map(string)
  default = {}
}
