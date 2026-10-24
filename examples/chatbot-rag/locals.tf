locals {
  # context.tags (open in the spec); the set comes from the stage file.
  tags = var.tags

  # resources.virtual-network.subnet_policy.subnet_delegations (forced by app-service.networking.integration_subnet)
  subnet_delegations = [
    { subnet = "snet-web", service = "Microsoft.Web/serverFarms" },
  ]

  # wiring.private_dns_zones: one zone per private link group, created and linked by this
  # deployment (private_dns_ownership: deployment). The key names the group in res.private_endpoints.tf.
  private_dns_zones = {
    blob              = "privatelink.blob.core.windows.net"
    vault             = "privatelink.vaultcore.azure.net"
    cognitiveservices = "privatelink.cognitiveservices.azure.com"
    openai            = "privatelink.openai.azure.com"
    aiservices        = "privatelink.services.ai.azure.com"
    search            = "privatelink.search.windows.net"
    sites             = "privatelink.azurewebsites.net"
    monitor           = "privatelink.monitor.azure.com"
  }

  # The system-assigned identities that identity.role_assignments refers to by name.
  principal_ids = {
    app-service    = azurerm_linux_web_app.this.identity[0].principal_id
    search-service = azurerm_search_service.this.identity[0].principal_id
  }

  # The scope of each role assignment, named like the resource in the spec.
  role_scopes = {
    application-insights = azurerm_application_insights.this.id
    key-vault            = azurerm_key_vault.this.id
    storage-account      = azurerm_storage_account.this.id
    foundry              = azurerm_cognitive_account.this.id
    search-service       = azurerm_search_service.this.id
  }
}
