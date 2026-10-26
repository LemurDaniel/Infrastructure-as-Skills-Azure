# Two storage accounts in the data resource group: the data lake (telemetry archive, Event Grid source,
# Backup vault target) and the function app's host storage. Both are private-only.

module "naming_datalake" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = concat(var.naming_suffix, ["dl"])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_host" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = concat(var.naming_suffix, ["host"])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_private_endpoint" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(["dl-blob", "dl-dfs", "host-blob", "host-queue"])

  suffix        = concat(var.naming_suffix, [each.key])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "storage_datalake" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "~> 0.10.0"

  name      = module.naming_datalake.storage_account.name_unique
  location  = var.location
  parent_id = var.resource_groups["data"].id

  # decision: storage-account__datalake.storage_kind - a data lake: StorageV2 with the hierarchical namespace
  account_kind   = "StorageV2"
  is_hns_enabled = true

  # decision: storage-account__datalake.data_protection.replication
  # account_sku_name carries tier and replication; the module's default Standard_ZRS would override a pair.
  account_sku_name = "Standard_LRS"
  # decision: storage-account__datalake.data_protection.access_tier
  access_tier = "Hot"

  # Private only (deployment.network_exposure): the bypass lets trusted Azure services (Event Grid, Backup) in.
  public_network_access_enabled = false
  network_rules = {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  # Explicit although several match the module default: a module minor cannot move them.
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  # deployment.local_auth: disabled - access is Entra ID and RBAC.
  shared_access_key_enabled = false
  sftp_enabled              = false
  # Settable only at creation. The module default is false.
  infrastructure_encryption_enabled = true

  # System identity: Event Hubs capture and Backup write through their own identities, this account has no reach outward.
  managed_identities = {}

  blob_properties = {
    # decision: storage-account__datalake.data_protection.versioning_enabled
    versioning_enabled = false
    # decision: storage-account__datalake.data_protection.blob_soft_delete_days - 0 days: off, written as disabled
    delete_retention_policy = {
      enabled = false
    }
    # decision: storage-account__datalake.data_protection.container_soft_delete_days - 0 days: off, written as disabled
    container_delete_retention_policy = {
      enabled = false
    }
    change_feed = { enabled = false }
  }

  # decision: blob-container.containers.container_names - telemetry, the Event Hubs archive target
  containers = {
    telemetry = {
      name                              = "telemetry"
      public_access                     = "None"
      immutable_storage_with_versioning = { enabled = false }
    }
  }

  # decision: storage-account__datalake.networking.private_endpoint_subresources
  private_endpoints = {
    for sub in ["blob", "dfs"] : sub => {
      name                          = module.naming_private_endpoint["dl-${sub}"].private_endpoint.name
      subnet_resource_id            = var.private_endpoint_subnet_id
      subresource_name              = sub
      private_dns_zone_resource_ids = [var.private_dns_zone_ids["privatelink.${sub}.core.windows.net"]]
    }
  }
  private_endpoints_manage_dns_zone_group = true # deployment.private_dns_records: deployment

  diagnostic_settings_storage_account = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "Transaction" }]
    }
  }
  diagnostic_settings_blob = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs                  = [{ category_group = "audit" }]
      metrics               = [{ category = "Transaction" }]
    }
  }

  # deployment.resource_lock: production
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}

module "storage_host" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "~> 0.10.0"

  name      = module.naming_host.storage_account.name_unique
  location  = var.location
  parent_id = var.resource_groups["data"].id

  account_kind = "StorageV2"
  # decision: storage-account__host.data_protection.replication
  account_sku_name = "Standard_LRS"
  access_tier      = "Hot"

  public_network_access_enabled = false
  network_rules = {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  https_traffic_only_enabled        = true
  min_tls_version                   = "TLS1_2"
  allow_nested_items_to_be_public   = false
  shared_access_key_enabled         = false
  sftp_enabled                      = false
  infrastructure_encryption_enabled = true
  managed_identities                = {}

  blob_properties = {
    versioning_enabled      = false
    delete_retention_policy = { enabled = true, days = 7 }
  }

  # The Flex Consumption deployment package. Not a spec decision: the function app cannot start without it.
  containers = {
    app_package = {
      name          = "app-package"
      public_access = "None"
    }
  }

  # decision: storage-account__host.networking.private_endpoint_subresources
  private_endpoints = {
    for sub in ["blob", "queue"] : sub => {
      name                          = module.naming_private_endpoint["host-${sub}"].private_endpoint.name
      subnet_resource_id            = var.private_endpoint_subnet_id
      subresource_name              = sub
      private_dns_zone_resource_ids = [var.private_dns_zone_ids["privatelink.${sub}.core.windows.net"]]
    }
  }
  private_endpoints_manage_dns_zone_group = true # deployment.private_dns_records: deployment

  diagnostic_settings_storage_account = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "Transaction" }]
    }
  }
  diagnostic_settings_blob = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs                  = [{ category_group = "audit" }]
      metrics               = [{ category = "Transaction" }]
    }
  }

  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
