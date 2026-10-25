# Rendering a Recovery Services vault as Terraform

Mapping from the question set to the vault. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-recoveryservices-vault/azurerm` | **v1.3.3** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 1.3.3`; the module is
past 1.0, so the major is what breaks.

**AzAPI only**: it takes `resource_group_name` (a name) and requires `azapi ~> 2.12`, `modtm ~> 0.3`,
`random >= 3.5, < 4.0` and Terraform `>= 1.9` - **no `azurerm` constraint of its own**, so it
sits on 5.x beside other modules. The root's provider set is the union.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| (the vault's tier) | `sku` | **Required, no default.** `"Standard"` (also spelled `"RS0"`); the set has no decision for it |
| `storage_redundancy` | `storage_mode_type` | `GeoRedundant` (module default), `LocallyRedundant`, `ZoneRedundant`; **cannot change once an item is protected**; written |
| `cross_region_restore` | `cross_region_restore_enabled` | Module default **`true`**, needs `GeoRedundant`; written |
| `soft_delete` | `soft_delete_enabled` | `Enabled` (default), `Disabled`, `AlwaysOn`; `AlwaysOn` cannot be reverted. Written |
| `soft_delete_retention_days` | - | **No input** in this version; the platform default (14 days) applies. Named in the handover, `# not-testable:` |
| `immutability` | `immutability` | `Locked`, `Unlocked` (module default), `Disabled`; written |
| `multi_user_authorization`, `resource_guard` | `resource_guard_id`, `resource_guard_association_enabled`, `resource_guard_operation_requests` | Set the association flag to `true` whenever the id is supplied |
| `job_failure_alerts` | `alerts_for_all_job_failures_enabled` | Default `true`; written |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default **`true`** (Bicep: off) |
| `private_endpoint_subnet` | `private_endpoints = { vault = { subnet_resource_id, subresource_name = "AzureBackup" } }` | `subresource_name` is optional; written |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | A user-assigned key identity **does not support private endpoints for backup**: a private vault uses `managed_identities.system_assigned` |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `protected_resources` | `backup_protected_vm`, `backup_protected_file_share`, `backup_protected_workload` | Maps keyed by a name; the policy is referenced by key |
| `backup_schedule`, `retention_days` | `vm_backup_policy`, `file_share_backup_policy`, `workload_backup_policy` | `frequency` `Daily`/`Weekly`; `retention_daily` is a count; `policy_type` `V2` for an enhanced policy |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "recovery_vault" {
  source  = "Azure/avm-res-recoveryservices-vault/azurerm"
  version = "~> 1.3.3"

  name                = data.naming_name.recovery_vault.name
  location            = var.location
  resource_group_name = var.resource_group_name

  sku = "Standard"
  # decision: recovery-services-vault.vault.storage_redundancy - the module default is GeoRedundant
  storage_mode_type = "ZoneRedundant"
  # decision: recovery-services-vault.vault.cross_region_restore - the module default is true
  cross_region_restore_enabled = false
  # decision: recovery-services-vault.vault.soft_delete
  soft_delete_enabled = "Enabled"
  # decision: recovery-services-vault.vault.immutability
  immutability = "Disabled"
  # decision: recovery-services-vault.vault.multi_user_authorization
  resource_guard_association_enabled = false
  # decision: recovery-services-vault.vault.job_failure_alerts
  alerts_for_all_job_failures_enabled = true

  managed_identities = {
    system_assigned = true
  }

  # decision: recovery-services-vault.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  private_endpoints = {
    vault = {
      name               = data.naming_name.recovery_vault_private_endpoint.name
      subresource_name   = "AzureBackup"
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  vm_backup_policy    = var.vm_backup_policy
  backup_protected_vm = var.backup_protected_vm

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
      log_categories        = ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupAlerts", "AddonAzureBackupProtectedInstance"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.recovery_vault.resource_id }
```

### Tests

`mock_provider "azapi"` (and `modtm`) keep the plan credential-free; the vault is an
`azapi_resource`, so asserts target its `body.properties` (`publicNetworkAccess`,
`redundancySettings`, `securitySettings.immutabilitySettings.state`, `securitySettings.softDeleteSettings`)
- exact paths are read off a first `terraform test` on the pinned version. Private endpoint, role
assignments, diagnostic setting, policies and protected items are built by the module and marked
`# not-testable:` with a reason, as is `soft_delete_retention_days`, which the module has no input for.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_recovery_services_vault` |
|---|---|
| `storage_redundancy` | `storage_mode_type` |
| `cross_region_restore` | `cross_region_restore_enabled` |
| `soft_delete` | `soft_delete_enabled` (a bool on the provider); `AlwaysOn` is not expressible there and needs an `azapi_update_resource` on the vault - check the 5.x schema |
| `immutability` | `immutability` |
| `public_network_access` | `public_network_access_enabled` |
| `managed_identity` | `identity { type, identity_ids }` |
| `key_management` | `encryption { key_id, infrastructure_encryption_enabled, user_assigned_identity_id, use_system_assigned_identity }` |
| policies | `azurerm_backup_policy_vm`, `azurerm_backup_policy_file_share` |
| protected items | `azurerm_backup_protected_vm`, `azurerm_backup_protected_file_share` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
