output "ingress_subnet_ids" {
  description = "Identifiers for ingress/public subnets across providers."
  value = {
    aws   = [for s in aws_subnet.ingress : s.id]
    gcp   = [for s in google_compute_subnetwork.ingress : s.name]
    azure = [for s in azurerm_subnet.ingress : s.id]
  }
}

output "app_subnet_ids" {
  description = "Identifiers for application subnets."
  value = {
    aws   = [for s in aws_subnet.app : s.id]
    gcp   = [for s in google_compute_subnetwork.app : s.name]
    azure = [for s in azurerm_subnet.app : s.id]
  }
}

output "data_subnet_ids" {
  description = "Identifiers for stateful service subnets."
  value = {
    aws   = [for s in aws_subnet.data : s.id]
    gcp   = [for s in google_compute_subnetwork.data : s.name]
    azure = [for s in azurerm_subnet.data : s.id]
  }
}

output "vpc_id" {
  description = "ID of the primary network resource for the active provider."
  value = {
    aws   = local.is_aws ? aws_vpc.this[0].id : null
    gcp   = local.is_gcp ? google_compute_network.this[0].name : null
    azure = local.is_azure ? azurerm_virtual_network.this[0].id : null
  }
}
