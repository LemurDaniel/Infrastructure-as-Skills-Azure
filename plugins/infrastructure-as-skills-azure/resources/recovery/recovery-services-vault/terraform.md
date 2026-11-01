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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| (the vault's tier) | `sku` | **Required, no default.** `"Standard"` (also spelled `"RS0"`); the set has no decision for it |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
