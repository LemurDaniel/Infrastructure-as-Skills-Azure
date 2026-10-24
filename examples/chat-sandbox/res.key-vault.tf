# Key Vault - holds the Entra app's client secret, read by the chat application at start.

data "naming_name" "key_vault" {
  resource = "Azure::Microsoft.KeyVault/vaults"
}

resource "azurerm_key_vault" "this" {
  name                = data.naming_name.key_vault.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id

  # decision: key-vault.vault.sku - standard; premium exists for HSM keys only
  # (deployment.key_protection: software)
  sku_name = "standard"
  # decision: key-vault.vault.purge_protection - off, overridden: a throwaway sandbox is rebuilt often and purge protection cannot be switched off once on
  purge_protection_enabled = false
  # decision: key-vault.vault.soft_delete_retention_days - 7, overridden: the shortest window, so the name comes back after a week; fixed at creation
  soft_delete_retention_days = 7
  # decision: key-vault.vault.rbac_authorization - role assignments, not access policies
  # (local_auth: disabled)
  rbac_authorization_enabled = true

  # decision: key-vault.networking.public_network_access - enabled (overridden): the app
  # reads the secret from public, changing addresses; no allowlist.
  public_network_access_enabled = true
  network_acls {
    default_action = "Allow"
    # decision: key-vault.networking.network_acl_bypass - closed; it only matters while a
    # firewall is on, written so the posture is on the resource.
    bypass = "None"
  }

  # decision: key-vault.security.enabled_for_services - empty: none of the three legacy
  # paths that let a platform service read the vault without an identity of its own.
  enabled_for_deployment          = false
  enabled_for_disk_encryption     = false
  enabled_for_template_deployment = false

  # decision: key-vault.keys.key_management - platform_managed: the vault holds no
  # encryption keys, so no azurerm_key_vault_key is rendered.

  tags = local.tags
}

# decision: key-vault.security.secret_placeholders - the slot exists before the app's
# first start; the real value is written afterwards, outside this code, and the next
# apply must not overwrite it (ignore_changes). The identity that applies needs Key Vault
# Secrets Officer on the vault for this write - it is not among the spec's role
# assignments, see the handover.
locals {
  key_vault_secret_placeholders = ["entra-client-secret"]
}

resource "azurerm_key_vault_secret" "placeholder" {
  for_each = toset(local.key_vault_secret_placeholders)

  name         = each.key
  key_vault_id = azurerm_key_vault.this.id
  value        = "placeholder - replace after deployment"
  content_type = "placeholder"

  lifecycle {
    ignore_changes = [value, tags]
  }
}

# decision: key-vault.observability.diagnostic_categories
locals {
  key_vault_log_categories = ["AuditEvent", "AzurePolicyEvaluationDetails"]
}

resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "diag"
  target_resource_id         = azurerm_key_vault.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(local.key_vault_log_categories)
    content {
      category = enabled_log.value
    }
  }

  # decision: key-vault.observability.metrics_enabled
  enabled_metric {
    category = "AllMetrics"
  }
}
