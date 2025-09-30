variable "cloud" {
  type        = string
  description = "Cloud provider identifier."
}

variable "environment" {
  type        = string
  description = "Deployment environment label."
}

variable "cluster_version" {
  type        = string
  description = "Desired Kubernetes version."
}

variable "subnet_ids" {
  type        = map(list(string))
  description = "Map of subnet IDs keyed by tier (ingress, app, data)."
}

variable "tags" {
  type        = map(string)
  default     = {}
}

variable "node_pools" {
  description = "Node pool configuration keyed by pool name."
  type = map(object({
    instance_type = string
    min_size      = number
    max_size      = number
    labels        = map(string)
    taints        = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
}
