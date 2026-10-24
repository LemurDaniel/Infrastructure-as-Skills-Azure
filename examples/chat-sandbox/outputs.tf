output "web_app_default_hostname" {
  description = "The app's public hostname."
  value       = azurerm_linux_web_app.this.default_hostname
}

output "web_app_principal_id" {
  description = "The app's system-assigned identity, for roles granted outside this root (AcrPull on the image registry)."
  value       = azurerm_linux_web_app.this.identity[0].principal_id
}

output "foundry_endpoint" {
  description = "The AI Foundry account's endpoint."
  value       = azurerm_cognitive_account.this.endpoint
}

output "foundry_project_ids" {
  description = "The Foundry projects, by the spec's project name."
  value       = { for k, p in azurerm_cognitive_account_project.this : k => p.id }
}

output "search_service_name" {
  description = "The search service; its endpoint is https://<name>.search.windows.net."
  value       = azurerm_search_service.this.name
}

output "storage_account_name" {
  description = "The storage account the app and the indexer use."
  value       = azurerm_storage_account.this.name
}

output "key_vault_uri" {
  description = "The vault the app reads entra-client-secret from."
  value       = azurerm_key_vault.this.vault_uri
}

output "log_analytics_workspace_id" {
  description = "The workspace every diagnostic setting routes to."
  value       = azurerm_log_analytics_workspace.this.id
}
