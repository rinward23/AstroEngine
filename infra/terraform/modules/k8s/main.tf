locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"

  tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "k8s"
  })
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.0"
  count           = local.is_aws ? 1 : 0
  cluster_name    = "astroengine-${var.environment}"
  cluster_version = var.cluster_version
  subnet_ids      = var.subnet_ids["app"]
  vpc_id          = var.tags["vpc_id"]
  tags            = local.tags

  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  eks_managed_node_groups = {
    for name, cfg in var.node_pools : name => {
      instance_types = [cfg.instance_type]
      min_size       = cfg.min_size
      max_size       = cfg.max_size
      desired_size   = cfg.min_size
      labels         = cfg.labels
      taints         = [for t in cfg.taints : {
        key    = t.key
        value  = t.value
        effect = t.effect
      }]
    }
  }
}

resource "google_container_cluster" "primary" {
  count                     = local.is_gcp ? 1 : 0
  name                      = "astroengine-${var.environment}"
  location                  = var.tags["region"]
  remove_default_node_pool  = true
  initial_node_count        = 1
  networking_mode           = "VPC_NATIVE"
  network                   = var.tags["vpc_name"]
  subnetwork                = var.subnet_ids["app"][0]
  resource_labels           = local.tags
  master_authorized_networks_config {
    cidr_blocks = [for cidr in var.subnet_ids["ingress"] : {
      cidr_block   = cidr
      display_name = "ingress-${cidr}"
    }]
  }
  release_channel {
    channel = "REGULAR"
  }
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
}

resource "google_container_node_pool" "primary_pools" {
  count    = local.is_gcp ? length(var.node_pools) : 0
  name     = "astroengine-${var.environment}-${element(keys(var.node_pools), count.index)}"
  cluster  = google_container_cluster.primary[0].name
  location = var.tags["region"]

  node_config {
    machine_type = values(var.node_pools)[count.index].instance_type
    labels       = values(var.node_pools)[count.index].labels
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    dynamic "taint" {
      for_each = values(var.node_pools)[count.index].taints
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }

  autoscaling {
    min_node_count = values(var.node_pools)[count.index].min_size
    max_node_count = values(var.node_pools)[count.index].max_size
  }
}

resource "azurerm_kubernetes_cluster" "this" {
  count               = local.is_azure ? 1 : 0
  name                = "aks-astroengine-${var.environment}"
  location            = var.tags["region"]
  resource_group_name = var.tags["resource_group"]
  dns_prefix          = "astroengine-${var.environment}"
  kubernetes_version  = var.cluster_version

  default_node_pool {
    name            = "system"
    vm_size         = values(var.node_pools)[0].instance_type
    node_count      = values(var.node_pools)[0].min_size
    vnet_subnet_id  = var.subnet_ids["app"][0]
    enable_auto_scaling = true
    min_count       = values(var.node_pools)[0].min_size
    max_count       = values(var.node_pools)[0].max_size
  }

  identity {
    type = "SystemAssigned"
  }

  role_based_access_control_enabled = true
  oidc_issuer_enabled               = true

  tags = local.tags
}
