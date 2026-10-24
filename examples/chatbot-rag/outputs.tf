output "virtual_network_id" {
  description = "Id of the deployment's virtual network."
  value       = azurerm_virtual_network.this.id
}

output "subnet_ids" {
  description = "Subnet ids keyed by subnet name."
  value       = { for k, s in azurerm_subnet.this : k => s.id }
}

output "log_analytics_workspace_id" {
  description = "Id of the deployment's workspace."
  value       = azurerm_log_analytics_workspace.this.id
}

output "foundry_endpoint" {
  description = "Endpoint of the Foundry account."
  value       = azurerm_cognitive_account.this.endpoint
}

output "search_endpoint" {
  description = "Endpoint of the search service."
  value       = azurerm_search_service.this.endpoint
}

output "app_service_default_hostname" {
  description = "Default host name of the web app; resolves to the private endpoint inside the network."
  value       = azurerm_linux_web_app.this.default_hostname
}

output "principal_ids" {
  description = "Principal ids of the system-assigned identities, keyed by resource."
  value = {
    app-service     = azurerm_linux_web_app.this.identity[0].principal_id
    search-service  = azurerm_search_service.this.identity[0].principal_id
    storage-account = azurerm_storage_account.this.identity[0].principal_id
    foundry         = azurerm_cognitive_account.this.identity[0].principal_id
  }
}
