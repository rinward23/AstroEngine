output "bucket_reference" {
  value = {
    aws   = local.is_aws ? aws_s3_bucket.this[0].id : null
    gcp   = local.is_gcp ? google_storage_bucket.this[0].name : null
    azure = local.is_azure ? azurerm_storage_container.this[0].id : null
  }
  description = "Provider-specific bucket or container reference."
}
