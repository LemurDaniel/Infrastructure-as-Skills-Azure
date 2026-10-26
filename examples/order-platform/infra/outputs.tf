output "resource_group_names" {
  description = "Names of the created resource groups by role."
  value       = { for role, rg in local.resource_groups : role => rg.name }
}

output "vnet_id" {
  description = "Virtual network of the stage."
  value       = module.network.vnet_id
}

output "front_door_id" {
  description = "Front Door profile, the only public entry."
  value       = module.network.front_door_id
}

output "apim_gateway_url" {
  description = "API Management gateway URL (internal)."
  value       = module.app.apim_gateway_url
}

output "function_app_id" {
  description = "Function app."
  value       = module.app.function_app_id
}
