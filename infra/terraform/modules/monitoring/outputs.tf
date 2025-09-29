output "workspace_arn" {
  value = {
    aws   = local.is_aws ? aws_prometheus_workspace.this[0].arn : null
    gcp   = null
    azure = null
  }
}

output "alert_channels" {
  value       = var.alert_endpoints
  description = "Alert routing identifiers."
}
