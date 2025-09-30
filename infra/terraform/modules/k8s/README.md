# Kubernetes Module

This module provisions the managed Kubernetes control plane and attaches worker node groups tuned for AstroEngine's workloads.  It consumes the network outputs so that pods and load balancers reside in private subnets while ingress controllers are exposed through controlled entry points.

Highlights:

* Supports EKS, GKE, and AKS creation with standardized labels and logging.
* Emits kubeconfig artifacts and OIDC issuer URLs for downstream identity providers.
* Configures cluster logging and enables workload identity integration for secretless deployments.
* Exposes output maps so Helmfile releases can derive namespaces, node selectors, and autoscaling parameters per environment.
