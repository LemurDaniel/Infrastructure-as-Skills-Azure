# Rendering a Backup vault as Terraform

Mapping from the question set to the vault. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-dataprotection-backupvault/azurerm` | **v2.0.9** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 2.0.9`; the module is
past 1.0, so the major is what breaks.

**AzAPI-based with a wide `azurerm` range**: it takes `resource_group_name` (a name) and requires
`azapi ~> 2.5`, `azurerm >= 4.2, < 6.0` - **it works on 5.x** - plus `modtm ~> 0.3`,
`random >= 3.5, < 4.0`, `time >= 0.9`, and Terraform `>= 1.9`. The module waits
(`wait_for_backup_instance_configure_duration`, 180 s) after a backup instance for protection to
leave `ConfiguringProtection`.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `storage_redundancy` | `redundancy` | `GeoRedundant`, `LocallyRedundant`, `ZoneRedundant`; **required**; changing forces a new vault |
| (the vault's datastore) | `datastore_type` | **Required**; `VaultStore` for a vaulted backup; the set does not decide it |
| `cross_region_restore` | `cross_region_restore_enabled` | Default `false`; written; only with `GeoRedundant` |
| `immutability` | `immutability` | `Disabled`, `Unlocked`, `Locked`; module default `Disabled`; written |
| (soft delete state) | `soft_delete` | **`AlwaysOn` and not changeable** with the current API version (2025-09-01); not a question |
| `soft_delete_retention_days` | `retention_duration_in_days` | 14-180; default 14; written |
| `multi_user_authorization`, `resource_guard` | `resource_guard_enabled`, `resource_guard_resource_id` | Pass the id of the guard in the security team's subscription; with `resource_guard_enabled = true` and no id the module creates a guard **in the same resource group**, which protects nothing against that group's administrators - never rely on that for `isolated` |
| `infrastructure_encryption` | - | **No input**; taken from the platform. `# not-testable:` and named in the handover |
| `job_failure_alerts` | `alerts_for_all_job_failures` | `"Enabled"` / `"Disabled"`; module default `null` (unset); written |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key` | Read the member names for the pinned version; needs `user_assigned` identity |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `protected_resources` | `backup_instances = { <k> = { name, backup_policy_key, ... } }` | Types `disk`, `blob`, `adls`, `kubernetes`, `postgresql`, `postgresql_flexible`; type-specific members in the README |
| `backup_schedule`, `retention_days` | `backup_policies = { <k> = { ... } }` | Read the policy shape for the datasource type from the README |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "backup_vault" {
  source  = "Azure/avm-res-dataprotection-backupvault/azurerm"
  version = "~> 2.0.9"

  name                = data.naming_name.backup_vault.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: backup-vault.vault.storage_redundancy - changing forces a new vault
  redundancy     = "ZoneRedundant"
  datastore_type = "VaultStore"
  # decision: backup-vault.vault.cross_region_restore
  cross_region_restore_enabled = false
  # decision: backup-vault.vault.immutability
  immutability = "Disabled"
  # decision: backup-vault.vault.soft_delete_retention_days
  retention_duration_in_days = 14
  # decision: backup-vault.vault.multi_user_authorization
  resource_guard_enabled = false
  # decision: backup-vault.vault.job_failure_alerts
  alerts_for_all_job_failures = "Enabled"

  managed_identities = {
    system_assigned = true
  }

  backup_policies  = var.backup_policies
  backup_instances = var.backup_instances

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
      principal_type             = v.principal_type
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupProtectedInstance"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.backup_vault.resource_id }
```

The output that carries the identity's principal id is read from the README for the pinned version. The vault's
identity is granted its role on every protected resource (`Storage Account Backup Contributor`
on a storage account, `Disk Backup Reader` and `Disk Snapshot Contributor` for a disk) **before**
the backup instance is created: the pattern orders it, and the module's wait absorbs only the
service-side delay.

### Tests

`mock_provider "azapi"` (and `modtm`, `azurerm`) keep the plan credential-free; the vault is an
`azapi_resource`, so asserts target its `body.properties` (`storageSettings` for the redundancy,
`securitySettings.immutabilitySettings.state`, `softDeleteSettings`, `monitoringSettings`) - exact
paths are read off a first `terraform test` on the pinned version. Role assignments, the
diagnostic setting, backup instances and `infrastructure_encryption` are marked `# not-testable:`
with a reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_data_protection_backup_vault` |
|---|---|
| `storage_redundancy` | `redundancy` |
| `cross_region_restore` | `cross_region_restore_enabled` |
| `immutability` | `immutability` |
| `soft_delete_retention_days` | `retention_duration_in_days`, `soft_delete` |
| `managed_identity` | `identity { type }` |
| `protected_resources` | `azurerm_data_protection_backup_instance_blob_storage`, `..._disk`, `..._postgresql_flexible_server`, `..._kubernetes_cluster` and a matching `azurerm_data_protection_backup_policy_*` |
| resource guard | `azurerm_data_protection_resource_guard` in the security subscription |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
