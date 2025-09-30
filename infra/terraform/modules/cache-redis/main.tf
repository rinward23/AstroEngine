locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"

  tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "redis"
  })
}

resource "aws_elasticache_subnet_group" "this" {
  count      = local.is_aws ? 1 : 0
  name       = "ae-${var.environment}-redis"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_replication_group" "this" {
  count                       = local.is_aws ? 1 : 0
  replication_group_id        = "ae-${var.environment}-redis"
  replication_group_description = "AstroEngine cache"
  engine                      = "redis"
  engine_version              = "7.0"
  node_type                   = var.instance_class
  number_cache_clusters       = 2
  automatic_failover_enabled  = true
  transit_encryption_enabled  = true
  at_rest_encryption_enabled  = true
  auth_token                  = random_password.redis.result
  subnet_group_name           = aws_elasticache_subnet_group.this[0].name
  security_group_ids          = [var.tags["redis_security_group"]]
  tags                        = local.tags
}

resource "google_redis_instance" "this" {
  count         = local.is_gcp ? 1 : 0
  name          = "ae-${var.environment}-redis"
  tier          = "STANDARD_HA"
  memory_size_gb = 5
  region        = var.tags["region"]
  authorized_network = var.tags["vpc_name"]
  transit_encryption_mode = "SERVER_AUTHENTICATION"
}

resource "azurerm_redis_cache" "this" {
  count               = local.is_azure ? 1 : 0
  name                = "aeredis-${var.environment}"
  location            = var.tags["region"]
  resource_group_name = var.tags["resource_group"]
  sku_name            = var.instance_class
  capacity            = 2
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
}

resource "random_password" "redis" {
  length  = 32
  special = false
}
