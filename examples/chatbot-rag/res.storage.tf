data "naming_name" "storage_account" {
  resource = "Azure::Microsoft.Storage/storageAccounts"
}

resource "azurerm_storage_account" "this" {
  name                = data.naming_name.storage_account.name
  resource_group_name = var.resource_group_name
  location            = var.location

  account_tier             = "Standard"
  account_kind             = "StorageV2"
  account_replication_type = "LRS" # data_protection.replication
  access_tier              = "Hot" # data_protection.access_tier

  # networking.public_network_access: disabled. No network_rules block: with public access off the
  # ACL has nothing to filter, and allow_azure_services_bypass is not rendered.
  public_network_access = "Disabled"

  # Explicit although several match the provider default: a reviewer can see a decision that was
  # made, and a provider major version cannot move it.
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  # Access is via Entra ID and RBAC. A key would bypass both and is not attributable in the audit log.
  shared_access_key_enabled = false
  sftp_enabled              = false

  # Settable only at creation - changing it later replaces the account.
  infrastructure_encryption_enabled = true

  # security.key_management: platform_managed - no customer_managed_key block.

  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = false

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }

    # point_in_time_restore_days: 0 - no restore_policy block.
  }

  # immutability: none - no immutability_policy block.

  tags = local.tags
}
