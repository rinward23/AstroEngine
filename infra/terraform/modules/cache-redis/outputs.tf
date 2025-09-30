output "endpoint" {
  value = {
    aws   = local.is_aws ? aws_elasticache_replication_group.this[0].primary_endpoint_address : null
    gcp   = local.is_gcp ? google_redis_instance.this[0].host : null
    azure = local.is_azure ? azurerm_redis_cache.this[0].hostname : null
  }
  description = "Hostname for Redis connection."
}

output "port" {
  value = {
    aws   = 6379
    gcp   = local.is_gcp ? google_redis_instance.this[0].port : null
    azure = 6380
  }
}

output "auth_token" {
  value       = random_password.redis.result
  sensitive   = true
  description = "Redis authentication secret or primary key."
}
