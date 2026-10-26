# Wiring between families: role assignments need both ends, so only the root can write them.
# (wiring.access in the spec: function-app <-> service-bus, event-hubs -> storage-account__datalake)

locals {
  function_roles = {
    host_blob  = { scope = module.data.host_storage_id, role = "Storage Blob Data Owner" }
    host_queue = { scope = module.data.host_storage_id, role = "Storage Queue Data Contributor" }
    sb_send    = { scope = module.messaging.service_bus_id, role = "Azure Service Bus Data Sender" }
    sb_receive = { scope = module.messaging.service_bus_id, role = "Azure Service Bus Data Receiver" }
  }
}

# The function app's identity: its host storage (identity-based, never a key) and Service Bus
# (sends orders and payments, processes billing/shipping/audit).
resource "azurerm_role_assignment" "function" {
  for_each = local.function_roles

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = module.security.identity_principal_ids["function"]
  principal_type       = "ServicePrincipal"
}

# The Event Hubs namespace writes its archive (capture) into the data lake with its own identity.
resource "azurerm_role_assignment" "event_hubs_archive" {
  scope                = module.data.datalake_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.messaging.event_hubs_principal_id
  principal_type       = "ServicePrincipal"
}
