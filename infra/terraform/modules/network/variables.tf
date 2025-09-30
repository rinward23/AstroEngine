variable "cloud" {
  type        = string
  description = "Cloud provider identifier (aws|gcp|azure)."
}

variable "environment" {
  type        = string
  description = "Deployment environment label (dev, staging, prod)."
}

variable "cidr_block" {
  type        = string
  description = "Primary CIDR block for the virtual network."
}

variable "ingress_subnets" {
  type        = list(string)
  description = "CIDR blocks for ingress/public subnets."
}

variable "app_subnets" {
  type        = list(string)
  description = "CIDR blocks for application/private subnets."
}

variable "data_subnets" {
  type        = list(string)
  description = "CIDR blocks for stateful service subnets."
}

variable "tags" {
  type        = map(string)
  description = "Common tags or labels for resources."
  default     = {}
}
