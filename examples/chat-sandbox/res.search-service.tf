# AI Search - the index over the documents (RAG).

data "naming_name" "search_service" {
  resource = "Azure::Microsoft.Search/searchServices"
}

resource "azurerm_search_service" "this" {
  name                = data.naming_name.search_service.name
  resource_group_name = var.resource_group_name
  location            = var.location

  # decision: search-service.service.sku - basic, the non_production_default a [sandbox] stack takes (forced by environments); fixed at creation
  sku = "basic"
  # decision: search-service.service.replica_count - outage_impact: tolerable
  replica_count = 1
  # decision: search-service.service.partition_count
  partition_count = 1
  # decision: search-service.service.semantic_ranker - free allowance
  semantic_search_sku = "free"

  # decision: search-service.networking.public_network_access - enabled (overridden): the
  # app queries from public, changing addresses; no allowlist.
  public_network_access_enabled = true
  # decision: search-service.networking.network_rule_bypass - closed; only matters while a
  # firewall is on, written so the posture is on the resource.
  network_rule_bypass_option = "None"

  # decision: search-service.identity.managed_identity - the identity that reads the
  # storage account and calls the embedding model.
  identity {
    type = "SystemAssigned"
  }

  # decision: search-service.security.local_authentication_disabled - inverse argument;
  # the admin key is gone, clients hold a role.
  local_authentication_enabled = false
  # decision: search-service.security.key_management - platform_managed: no CMK enforcement

  tags = local.tags
}

# decision: search-service.observability.diagnostic_categories
locals {
  search_log_categories = ["OperationLogs"]
}

resource "azurerm_monitor_diagnostic_setting" "search_service" {
  name                       = "diag"
  target_resource_id         = azurerm_search_service.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(local.search_log_categories)
    content {
      category = enabled_log.value
    }
  }

  # decision: search-service.observability.metrics_enabled
  enabled_metric {
    category = "AllMetrics"
  }
}
