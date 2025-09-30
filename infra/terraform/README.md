# Terraform Stack

This directory contains composable Terraform modules used to provision AstroEngine's infrastructure across dev, staging, and production.  Modules are intentionally cloud-agnostic, supporting AWS, Google Cloud, and Azure through conditional resources.  They expose consistent outputs so downstream automation (Helmfile, CI/CD workflows) can consume them without environment-specific branching.

Recommended layout:

```hcl
module "network" { ... }
module "k8s"     { ... }
module "database" { ... }
module "redis"   { ... }
module "storage" { ... }
module "monitor" { ... }
```

Use separate state files per environment to preserve immutability and isolate blast radius.
