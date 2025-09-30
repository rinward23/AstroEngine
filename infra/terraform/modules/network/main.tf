locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"

  common_tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "network"
  })
}

# AWS network primitives
resource "aws_vpc" "this" {
  count                = local.is_aws ? 1 : 0
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = local.common_tags
}

resource "aws_flow_log" "this" {
  count                = local.is_aws ? 1 : 0
  log_destination_type = "cloud-watch-logs"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.this[0].id
  tags                 = local.common_tags
}

resource "aws_subnet" "ingress" {
  count             = local.is_aws ? length(var.ingress_subnets) : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = var.ingress_subnets[count.index]
  map_public_ip_on_launch = true
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
  tags              = merge(local.common_tags, { "astroengine:tier" = "ingress" })
}

data "aws_availability_zones" "available" {
  count = local.is_aws ? 1 : 0
  state = "available"
}

resource "aws_subnet" "app" {
  count             = local.is_aws ? length(var.app_subnets) : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = var.app_subnets[count.index]
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
  tags              = merge(local.common_tags, { "astroengine:tier" = "app" })
}

resource "aws_subnet" "data" {
  count             = local.is_aws ? length(var.data_subnets) : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = var.data_subnets[count.index]
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
  tags              = merge(local.common_tags, { "astroengine:tier" = "data" })
}

# Google Cloud network primitives
resource "google_compute_network" "this" {
  count                   = local.is_gcp ? 1 : 0
  name                    = "astroengine-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "ingress" {
  count         = local.is_gcp ? length(var.ingress_subnets) : 0
  name          = "astroengine-${var.environment}-ingress-${count.index}"
  ip_cidr_range = var.ingress_subnets[count.index]
  network       = google_compute_network.this[0].name
  region        = var.tags["region"]
  purpose       = "PRIVATE"
}

resource "google_compute_subnetwork" "app" {
  count         = local.is_gcp ? length(var.app_subnets) : 0
  name          = "astroengine-${var.environment}-app-${count.index}"
  ip_cidr_range = var.app_subnets[count.index]
  network       = google_compute_network.this[0].name
  region        = var.tags["region"]
}

resource "google_compute_subnetwork" "data" {
  count         = local.is_gcp ? length(var.data_subnets) : 0
  name          = "astroengine-${var.environment}-data-${count.index}"
  ip_cidr_range = var.data_subnets[count.index]
  network       = google_compute_network.this[0].name
  region        = var.tags["region"]
  private_ip_google_access = true
}

# Azure network primitives
resource "azurerm_resource_group" "this" {
  count    = local.is_azure ? 1 : 0
  name     = "rg-astroengine-${var.environment}"
  location = var.tags["region"]
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "this" {
  count               = local.is_azure ? 1 : 0
  name                = "vnet-astroengine-${var.environment}"
  address_space       = [var.cidr_block]
  location            = azurerm_resource_group.this[0].location
  resource_group_name = azurerm_resource_group.this[0].name
  tags                = local.common_tags
}

resource "azurerm_subnet" "ingress" {
  count                = local.is_azure ? length(var.ingress_subnets) : 0
  name                 = "snet-ingress-${count.index}"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = [var.ingress_subnets[count.index]]
}

resource "azurerm_subnet" "app" {
  count                = local.is_azure ? length(var.app_subnets) : 0
  name                 = "snet-app-${count.index}"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = [var.app_subnets[count.index]]
}

resource "azurerm_subnet" "data" {
  count                = local.is_azure ? length(var.data_subnets) : 0
  name                 = "snet-data-${count.index}"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = [var.data_subnets[count.index]]
}
