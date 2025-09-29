locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"

  tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "object-storage"
  })
}

resource "aws_s3_bucket" "this" {
  count  = local.is_aws ? 1 : 0
  bucket = var.bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "this" {
  count  = local.is_aws ? 1 : 0
  bucket = aws_s3_bucket.this[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count  = local.is_aws ? 1 : 0
  bucket = aws_s3_bucket.this[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count  = local.is_aws ? 1 : 0
  bucket = aws_s3_bucket.this[0].id
  rule {
    id     = "transition-archive"
    status = "Enabled"
    transition {
      days          = var.retention_days
      storage_class = "GLACIER"
    }
  }
}

resource "google_storage_bucket" "this" {
  count         = local.is_gcp ? 1 : 0
  name          = var.bucket_name
  location      = var.tags["region"]
  storage_class = "STANDARD"
  labels        = local.tags
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      age = var.retention_days
    }
    action {
      type = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  uniform_bucket_level_access = true
}

resource "azurerm_storage_account" "this" {
  count                    = local.is_azure ? 1 : 0
  name                     = substr(replace(var.bucket_name, "-", ""), 0, 24)
  resource_group_name      = var.tags["resource_group"]
  location                 = var.tags["region"]
  account_tier             = "Standard"
  account_replication_type = "GRS"
  tags                     = local.tags
}

resource "azurerm_storage_container" "this" {
  count                 = local.is_azure ? 1 : 0
  name                  = var.bucket_name
  storage_account_name  = azurerm_storage_account.this[0].name
  container_access_type = "private"
}
