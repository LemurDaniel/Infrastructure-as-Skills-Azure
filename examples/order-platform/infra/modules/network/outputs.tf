output "vnet_id" {
  description = "Resource id of the virtual network."
  value       = module.virtual_network.resource_id
}

output "subnet_ids" {
  description = "Subnet ids by subnet name."
  value       = { for name, s in module.virtual_network.subnets : name => s.resource_id }
}

output "appgw_backend_fqdn" {
  description = "Public address of the Application Gateway, the origin Front Door calls."
  value       = module.public_ip_appgw.public_ip_address
}

output "front_door_id" {
  description = "Resource id of the Front Door profile."
  value       = module.front_door.resource_id
}

output "private_dns_zone_ids" {
  description = "Private DNS zone ids by zone name, for the private endpoints of the other families."
  value       = { for name, z in module.private_dns_zone : name => z.resource_id }
}
