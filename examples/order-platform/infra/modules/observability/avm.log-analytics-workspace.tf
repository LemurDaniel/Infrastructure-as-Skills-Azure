module "naming" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

# observability_ownership: create - the workspace of the stage; the other families send their diagnostics here.
module "workspace" {
  source  = "Azure/avm-res-operationalinsights-workspace/azurerm"
  version = "~> 0.5.1"

  name                = module.naming.log_analytics_workspace.name
  location            = var.location
  resource_group_name = var.resource_groups["observability"].name

  log_analytics_workspace_sku = "PerGB2018"
  # decision: log-analytics-workspace.cost.retention_days (deployment.log_retention_days)
  log_analytics_workspace_retention_in_days = 30
  # deployment.daily_quota_gb: -1 is no cap
  log_analytics_workspace_daily_quota_gb = -1

  # Private by default (deployment.network_exposure): neither ingestion nor query over the public internet.
  # Both, or logs arrive and nobody can read them; the other families reach it by Azure Monitor's own path.
  log_analytics_workspace_internet_ingestion_enabled = false
  log_analytics_workspace_internet_query_enabled     = false

  # deployment.local_auth: disabled - the workspace key is a non-expiring bearer credential. Module default is true.
  log_analytics_workspace_local_authentication_enabled = false

  # false: RBAC on the workspace governs reads, not the permissions of whichever resource emitted the row.
  log_analytics_workspace_allow_resource_only_permissions = false

  # deployment.resource_lock: production - the loss of the logs cannot be undone from the spec.
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
