locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"

  tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "database"
  })
}

resource "aws_rds_cluster" "aurora" {
  count              = local.is_aws ? 1 : 0
  engine             = "aurora-postgresql"
  engine_version     = var.db_version
  cluster_identifier = "astroengine-${var.environment}"
  master_username    = "astroengine"
  master_password    = random_password.master.result
  backup_retention_period = 7
  preferred_backup_window = "03:00-05:00"
  storage_encrypted  = true
  db_subnet_group_name = aws_db_subnet_group.this[0].name
  vpc_security_group_ids = [aws_security_group.db[0].id]
  tags               = local.tags
}

resource "aws_db_subnet_group" "this" {
  count       = local.is_aws ? 1 : 0
  name        = "astroengine-${var.environment}"
  subnet_ids  = var.subnet_ids
  tags        = local.tags
}

resource "aws_security_group" "db" {
  count  = local.is_aws ? 1 : 0
  name   = "astroengine-${var.environment}-db"
  vpc_id = var.tags["vpc_id"]
  tags   = local.tags
}

resource "aws_rds_cluster_instance" "aurora_instances" {
  count              = local.is_aws ? 2 : 0
  identifier         = "astroengine-${var.environment}-${count.index}"
  cluster_identifier = aws_rds_cluster.aurora[0].id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.aurora[0].engine
  engine_version     = aws_rds_cluster.aurora[0].engine_version
  publicly_accessible = false
}

resource "google_sql_database_instance" "postgres" {
  count             = local.is_gcp ? 1 : 0
  name              = "astroengine-${var.environment}"
  database_version  = "POSTGRES_${var.db_version}"
  region            = var.tags["region"]
  settings {
    tier                        = var.instance_class
    availability_type           = "REGIONAL"
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }
    disk_autoresize = true
    disk_size       = var.storage_gb
  }
  root_password = random_password.master.result
}

resource "azurerm_postgresql_flexible_server" "postgres" {
  count               = local.is_azure ? 1 : 0
  name                = "pg-astroengine-${var.environment}"
  location            = var.tags["region"]
  resource_group_name = var.tags["resource_group"]
  administrator_login = "astroengine"
  administrator_password = random_password.master.result
  version             = var.db_version
  sku_name            = var.instance_class
  storage_mb          = var.storage_gb * 1024
  high_availability {
    mode = "ZoneRedundant"
  }
  backup {
    backup_retention_days        = 7
    geo_redundant_backup_enabled = true
  }
  authentication {
    active_directory_auth_enabled = true
  }
}

resource "random_password" "master" {
  length           = 32
  special          = true
  override_characters = "!@#%^&*()-_=+"
}

resource "null_resource" "logical_backup" {
  triggers = {
    bucket = var.backup_bucket
  }
}
