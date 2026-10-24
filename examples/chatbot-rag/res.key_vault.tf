data "azurerm_client_config" "current" {}

data "naming_name" "key_vault" {
  resource = "Azure::Microsoft.KeyVault/vaults"
}

resource "azurerm_key_vault" "this" {
  name                = data.naming_name.key_vault.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id

  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 90

  # vault.rbac_authorization: true - no access_policy block and no azurerm_key_vault_access_policy.
  rbac_authorization_enabled = true

  # networking.public_network_access: disabled
  public_network_access_enabled = false
  network_acls {
    default_action = "Deny"
    bypass         = "None" # networking.network_acl_bypass
  }

  # security.enabled_for_services: [] - none of the three platform integrations
  enabled_for_deployment          = false
  enabled_for_disk_encryption     = false
  enabled_for_template_deployment = false

  tags = local.tags
}
