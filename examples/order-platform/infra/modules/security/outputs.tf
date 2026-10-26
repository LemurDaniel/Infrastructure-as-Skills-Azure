output "identity_ids" {
  description = "Resource ids of the user-assigned identities by purpose (function, appgw)."
  value       = { for k, i in module.identity : k => i.resource_id }
}

output "identity_principal_ids" {
  description = "Principal ids by purpose, for role assignments."
  value       = { for k, i in module.identity : k => i.principal_id }
}

output "identity_client_ids" {
  description = "Client ids by purpose, for the identity-based connections of the function app."
  value       = { for k, i in module.identity : k => i.client_id }
}
