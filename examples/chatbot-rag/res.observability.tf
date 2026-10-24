data "naming_name" "log_analytics_workspace" {
  resource = "Azure::Microsoft.OperationalInsights/workspaces"
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = data.naming_name.log_analytics_workspace.name
  resource_group_name = var.resource_group_name
  location            = var.location

  # cost.sku / cost.retention_days / cost.daily_quota_gb (retention and quota come from the deployment set)
  sku               = "PerGB2018"
  retention_in_days = 30
  daily_quota_gb    = -1

  # access.public_network_access: enabled - no Azure Monitor Private Link Scope exists in a
  # standalone landing zone, and a closed workspace without one receives nothing.
  internet_ingestion_access_type = "Enabled"
  internet_query_access_type     = "Enabled"

  # access.local_auth: false - the workspace key is a non-expiring bearer credential.
  local_authentication_enabled = false

  # access.rbac_only_access: true. The argument is the inverse: false means workspace RBAC governs
  # reads, rather than permissions inherited from whichever resource emitted the row.
  allow_resource_only_permissions = false

  # data_protection.immediate_purge_protection / archive_to_storage: see providers.tf
  # (permanently_delete_on_destroy = false); no archive destination is rendered.

  tags = local.tags
}

data "naming_name" "application_insights" {
  resource = "Azure::Microsoft.Insights/components"
}

resource "azurerm_application_insights" "this" {
  name                = data.naming_name.application_insights.name
  resource_group_name = var.resource_group_name
  location            = var.location

  # component.workspace: the deployment's own workspace (observability_ownership: create)
  workspace_id     = azurerm_log_analytics_workspace.this.id
  application_type = "web"

  # Follows the workspace, which owns the retention of a workspace-based component.
  retention_in_days = azurerm_log_analytics_workspace.this.retention_in_days

  sampling_percentage  = 100
  daily_data_cap_in_gb = 0    # daily_cap_gb: 0 - no cap
  ip_masking_enabled   = true # store_client_ip: false

  # networking.public_network_access: disabled. Telemetry reaches the component only through an
  # Azure Monitor Private Link Scope, which is open in the spec (private_link_scope) and not
  # rendered: until it is answered the SDKs of the app cannot send.
  internet_ingestion_enabled = false
  internet_query_enabled     = false

  # security.local_authentication_disabled: true - the app authenticates with Entra ID and needs
  # Monitoring Metrics Publisher (res.roles.tf).
  local_authentication_enabled = false

  tags = local.tags
}
