# Wiring between the resources: the roles each consumer's managed identity holds on the
# resource it calls (resources.<resource>.identity.role_assignments, per stage from the
# stage file; principals resolved here, where both ends are visible). Data-plane roles
# only, scoped to the resource, never to the subscription.

locals {
  # The resources that carry a system-assigned identity a role can be granted to.
  principal_ids = {
    "app-service"    = azurerm_linux_web_app.this.identity[0].principal_id
    "search-service" = azurerm_search_service.this.identity[0].principal_id
  }

  # The scope each spec resource key resolves to.
  role_scopes = {
    "foundry"         = azurerm_cognitive_account.this.id
    "search-service"  = azurerm_search_service.this.id
    "storage-account" = azurerm_storage_account.this.id
    "key-vault"       = azurerm_key_vault.this.id
  }

  role_assignments = merge([
    for resource, entries in var.role_assignments : {
      for e in entries : "${resource}/${e.principal}/${e.role}" => {
        scope        = local.role_scopes[resource]
        principal_id = local.principal_ids[e.principal]
        role         = e.role
      }
    }
  ]...)
}

resource "azurerm_role_assignment" "this" {
  for_each = local.role_assignments

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
  # A managed identity is a service principal; saying so skips the directory lookup that
  # fails while a new identity is still replicating.
  principal_type = "ServicePrincipal"
}
