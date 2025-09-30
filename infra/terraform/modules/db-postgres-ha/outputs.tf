output "primary_endpoint" {
  description = "Primary connection endpoint."
  value = {
    aws   = local.is_aws ? aws_rds_cluster.aurora[0].endpoint : null
    gcp   = local.is_gcp ? google_sql_database_instance.postgres[0].connection_name : null
    azure = local.is_azure ? azurerm_postgresql_flexible_server.postgres[0].fqdn : null
  }
}

output "reader_endpoint" {
  description = "Read replica endpoint when available."
  value = {
    aws   = local.is_aws ? aws_rds_cluster.aurora[0].reader_endpoint : null
    gcp   = local.is_gcp ? google_sql_database_instance.postgres[0].connection_name : null
    azure = local.is_azure ? azurerm_postgresql_flexible_server.postgres[0].fqdn : null
  }
}

output "admin_credentials" {
  description = "Admin credential secret references."
  value = {
    username = "astroengine"
    password = random_password.master.result
  }
  sensitive = true
}

output "backup_bucket" {
  value       = var.backup_bucket
  description = "Object storage location for logical backups."
}
