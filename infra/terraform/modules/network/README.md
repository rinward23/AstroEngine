# Network Module

This Terraform module provisions the shared network fabric that hosts the AstroEngine platform.  It supports AWS, Google Cloud, and Azure by mapping the requested provider into the appropriate primitives (VPC/VNet, subnets, and routing).  The module defaults to private subnets for data plane workloads and exposes only the ingress gateway through public endpoints that are protected by a WAF.

Key features:

* Creates three-tier subnets (ingress, application, data) with CIDR ranges supplied by the caller.
* Enables flow logs or packet mirroring for audit visibility in each provider.
* Publishes outputs that downstream modules (Kubernetes, PostgreSQL, Redis) can consume to attach to the network securely.
* Implements tagging/labeling conventions for tenancy attribution and cost reporting.

Usage example:

```hcl
module "network" {
  source          = "./modules/network"
  cloud           = var.cloud
  environment     = var.environment
  cidr_block      = "10.40.0.0/16"
  ingress_subnets = ["10.40.0.0/20", "10.40.16.0/20"]
  app_subnets     = ["10.40.32.0/20", "10.40.48.0/20"]
  data_subnets    = ["10.40.64.0/20", "10.40.80.0/20"]
  tags            = var.tags
}
```

The module intentionally avoids provider-specific outputs in favor of neutral names so that the wider IaC stack can be reused across clouds.
