# observability.diagnostic_workspace is log-analytics-workspace in every stage: the deployment's own
# workspace (observability_ownership: create). One setting per target; the storage account has two
# targets, the account (metrics only - it emits no log categories) and its blob service.
locals {
  diagnostics = {
    virtual-network = {
      target_id       = azurerm_virtual_network.this.id
      categories      = []
      category_groups = []
      metrics         = true # AllMetrics; the vnet set names no log category
    }
    network-security-group__endpoints = {
      target_id       = azurerm_network_security_group.this["endpoints"].id
      categories      = ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"]
      category_groups = []
      metrics         = false # a security group emits no metrics
    }
    network-security-group__integration = {
      target_id       = azurerm_network_security_group.this["integration"].id
      categories      = ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"]
      category_groups = []
      metrics         = false
    }
    key-vault = {
      target_id       = azurerm_key_vault.this.id
      categories      = ["AuditEvent", "AzurePolicyEvaluationDetails"]
      category_groups = []
      metrics         = true
    }
    storage-account = {
      target_id       = azurerm_storage_account.this.id
      categories      = []
      category_groups = []
      metrics         = true
    }
    storage-account-blob = {
      target_id       = "${azurerm_storage_account.this.id}/blobServices/default"
      categories      = []
      category_groups = ["audit"]
      metrics         = true
    }
    foundry = {
      target_id       = azurerm_cognitive_account.this.id
      categories      = ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"]
      category_groups = []
      metrics         = true
    }
    search-service = {
      target_id       = azurerm_search_service.this.id
      categories      = ["OperationLogs"]
      category_groups = []
      metrics         = true
    }
    app-service = {
      target_id       = azurerm_linux_web_app.this.id
      categories      = ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"]
      category_groups = []
      metrics         = true
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  for_each = local.diagnostics

  name                       = "diag"
  target_resource_id         = each.value.target_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(each.value.categories)
    content {
      category = enabled_log.value
    }
  }

  dynamic "enabled_log" {
    for_each = toset(each.value.category_groups)
    content {
      category_group = enabled_log.value
    }
  }

  dynamic "enabled_metric" {
    for_each = each.value.metrics ? ["AllMetrics"] : []
    content {
      category = enabled_metric.value
    }
  }
}
