# Log Analytics workspace - created here (deployment.observability_ownership: create, a
# standalone landing zone has no central workspace). Every other resource's diagnostic
# setting points at it.

data "naming_name" "log_analytics_workspace" {
  resource = "Azure::Microsoft.OperationalInsights/workspaces"
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = data.naming_name.log_analytics_workspace.name
  resource_group_name = var.resource_group_name
  location            = var.location

  # decision: log-analytics-workspace.cost.sku - pay as you go until the volume is known
  sku = "PerGB2018"
  # decision: log-analytics-workspace.cost.retention_days (deployment.log_retention_days)
  retention_in_days = 30
  # decision: log-analytics-workspace.cost.daily_quota_gb - -1 is no cap; a cap drops logs
  daily_quota_gb = -1

  # decision: log-analytics-workspace.access.public_network_access - enabled: a standalone
  # deployment has no Azure Monitor Private Link Scope to go through. Ingestion and query
  # are two switches, written together or the workspace is half-private.
  internet_ingestion_access_type = "Enabled"
  internet_query_access_type     = "Enabled"

  # decision: log-analytics-workspace.access.local_auth - the workspace key is a
  # non-expiring bearer credential; agents authenticate with Entra ID.
  local_authentication_enabled = false

  # decision: log-analytics-workspace.access.rbac_only_access - inverted argument: false
  # means RBAC on the workspace governs reads, not permissions inherited from the
  # resource that emitted the row.
  allow_resource_only_permissions = false

  # log-analytics-workspace.data_protection.immediate_purge_protection lives in the
  # provider's features block (providers.tf); archive_to_storage: false renders nothing.

  tags = local.tags
}
