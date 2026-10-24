# Storage account - the chat application's persistent data, indexed by the search service.

data "naming_name" "storage_account" {
  resource = "Azure::Microsoft.Storage/storageAccounts"
}

resource "azurerm_storage_account" "this" {
  name                = data.naming_name.storage_account.name
  resource_group_name = var.resource_group_name
  location            = var.location

  account_tier = "Standard"
  account_kind = "StorageV2"
  # decision: storage-account.data_protection.replication - outage_impact: tolerable
  account_replication_type = "LRS"
  # decision: storage-account.data_protection.access_tier - data_access_pattern: active
  access_tier = "Hot"

  # decision: storage-account.networking.public_network_access - enabled (overridden): the
  # app and the indexer reach it from public, changing addresses. A string on 5.x.
  public_network_access = "Enabled"
  network_rules {
    default_action = "Allow"
    # decision: storage-account.networking.allow_azure_services_bypass - platform features
    # (diagnostics delivery, backup) reach the account past the ACL.
    bypass = ["AzureServices"]
  }
  # storage-account.networking.private_endpoint_subresources: [blob] - no endpoint is
  # rendered, there is no network (deployment.network_ownership: none).

  # Explicit although several match the provider default: a reviewer sees a decision that
  # was made, and a provider major version cannot move it.
  # decision: storage-account.security.https_traffic_only
  https_traffic_only_enabled = true
  # decision: storage-account.security.min_tls_version
  min_tls_version = "TLS1_2"
  # decision: storage-account.security.allow_blob_public_access - the account-level switch
  # that makes anonymous container access possible at all.
  allow_nested_items_to_be_public = false
  # decision: storage-account.security.shared_access_key_enabled - access is via Entra ID
  # and RBAC; a key would bypass both and is not attributable.
  shared_access_key_enabled = false
  # decision: storage-account.security.sftp_enabled - SFTP brings local users
  sftp_enabled = false
  # decision: storage-account.security.infrastructure_encryption_enabled - settable only
  # at creation; changing it later replaces the account.
  infrastructure_encryption_enabled = true
  # decision: storage-account.security.key_management - platform_managed: no
  # customer_managed_key block.

  # decision: storage-account.identity.managed_identity
  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    # decision: storage-account.data_protection.versioning_enabled - protects against
    # overwrite, which soft delete does not.
    versioning_enabled = true
    # decision: storage-account.data_protection.change_feed_enabled
    change_feed_enabled = false

    # decision: storage-account.data_protection.blob_soft_delete_days - data_loss_tolerance:
    # one_week
    delete_retention_policy {
      days = 7
    }

    # decision: storage-account.data_protection.container_soft_delete_days
    container_delete_retention_policy {
      days = 7
    }

    # decision: storage-account.data_protection.point_in_time_restore_days - 0: no
    # restore_policy block.
  }
  # decision: storage-account.data_protection.immutability - none: no immutability_policy.

  tags = local.tags
}

# Two settings, because the account and its blob service are two diagnostic targets. The
# account itself emits no log categories; it gets metrics only.
resource "azurerm_monitor_diagnostic_setting" "storage_account" {
  name                       = "diag"
  target_resource_id         = azurerm_storage_account.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  # decision: storage-account.observability.metrics_enabled
  enabled_metric {
    category = "AllMetrics"
  }
}

# decision: storage-account.observability.diagnostic_categories - category groups on the
# blob service
locals {
  storage_blob_log_category_groups = ["audit"]
}

# Blob data-plane logs attach to <account>/blobServices/default. A setting on the account
# alone collects no StorageRead/Write/Delete while looking configured.
resource "azurerm_monitor_diagnostic_setting" "storage_blob" {
  name                       = "diag"
  target_resource_id         = "${azurerm_storage_account.this.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(local.storage_blob_log_category_groups)
    content {
      category_group = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
