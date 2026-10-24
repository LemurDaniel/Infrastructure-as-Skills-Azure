data "naming_name" "search_service" {
  resource = "Azure::Microsoft.Search/searchServices"
}

resource "azurerm_search_service" "this" {
  name                = data.naming_name.search_service.name
  resource_group_name = var.resource_group_name
  location            = var.location

  sku                 = var.search_sku # service.sku, per stage
  replica_count       = 1
  partition_count     = 1
  semantic_search_sku = "free"

  # networking.public_network_access: disabled; networking.network_rule_bypass: None
  public_network_access_enabled = false
  network_rule_bypass_option    = "None"

  # security.local_authentication_disabled: true (the argument is the inverse). Query and admin
  # keys are off; callers use their identity and the Search data-plane roles.
  local_authentication_enabled = false

  # security.key_management: platform_managed
  customer_managed_key_enforcement_enabled = false

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}
