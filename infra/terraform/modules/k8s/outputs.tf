output "cluster_name" {
  value       = coalesce(try(module.eks[0].cluster_name, null), try(google_container_cluster.primary[0].name, null), try(azurerm_kubernetes_cluster.this[0].name, null))
  description = "Name of the Kubernetes cluster."
}

output "kubeconfig" {
  description = "Rendered kubeconfig for the chosen provider."
  value = {
    aws   = local.is_aws ? module.eks[0].kubeconfig : null
    gcp   = local.is_gcp ? google_container_cluster.primary[0].endpoint : null
    azure = local.is_azure ? azurerm_kubernetes_cluster.this[0].kube_admin_config_raw : null
  }
  sensitive = true
}

output "oidc_issuer" {
  description = "OIDC issuer URL for workload identities."
  value = {
    aws   = local.is_aws ? module.eks[0].cluster_oidc_issuer_url : null
    gcp   = local.is_gcp ? google_container_cluster.primary[0].workload_identity_config[0].workload_pool : null
    azure = local.is_azure ? azurerm_kubernetes_cluster.this[0].oidc_issuer_url : null
  }
}
