# Rendering a Key Vault as Terraform

Mapping from the question set to the vault. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-keyvault-vault/azurerm` | **v0.12.0** | 2026-10-23 | **Orphaned** in the index |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.12.0`. An
`Orphaned` module works but has no owner: say so in the handover.

**Unlike the storage and App Service modules this one is `azurerm`-based.** It takes
`resource_group_name` (a name), requires `azurerm >= 4.81, < 5.0` - **a root calling it cannot
be on 5.x** - plus `azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.5`, `time ~> 0.9`, and
Terraform `>= 1.11`. The root's provider set is the union with the other modules; a root that
already calls an AzAPI module and this one carries both families.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "vault" {
  source  = "Azure/avm-res-keyvault-vault/azurerm"
  version = "~> 0.12.0"

  name                = data.naming_name.vault.name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.this.tenant_id

  # decision: key-vault.vault.sku - the module default is premium
  sku_name = "standard"
  # decision: key-vault.vault.purge_protection
  purge_protection_enabled = true
  # decision: key-vault.vault.soft_delete_retention_days
  soft_delete_retention_days = 90
  # decision: key-vault.vault.rbac_authorization - inverse input
  legacy_access_policies_enabled = false

  # decision: key-vault.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  network_acls = {
    bypass         = "None"
    default_action = "Deny"
    ip_rules       = []
  }
  private_endpoints = {
    vault = {
      name               = data.naming_name.vault_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: key-vault.security.enabled_for_services - all three written
  enabled_for_deployment          = false
  enabled_for_disk_encryption     = false
  enabled_for_template_deployment = false

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
      log_categories        = ["AuditEvent", "AzurePolicyEvaluationDetails"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.vault.resource_id }
output "uri" { value = module.vault.uri }
```

### Secret placeholders

Outside the module, so the value can be ignored. The identity that applies must be a writer
on the vault, and the vault reachable (see `notes.md`).

```hcl
resource "azurerm_key_vault_secret" "placeholder" {
  for_each = toset(var.secret_placeholders)

  name         = each.key
  key_vault_id = module.vault.resource_id
  value        = "placeholder - replace after deployment"
  content_type = "placeholder"

  lifecycle {
    ignore_changes = [value, tags]
  }

  depends_on = [module.vault]
}
```

### Tests

`mock_provider "azurerm"` (and `azapi`, `modtm`) keep the plan credential-free. The module is
`azurerm`-based, so its `resource` output is not an `azapi_resource` body; asserts target what
the plan shows (`sku_name`, purge protection, retention, the RBAC flag, network ACLs, the
public flag), and the exact output paths are read off a first `terraform test` run on the
pinned version, not recalled. What the module builds in child resources - the endpoint, the
diagnostic setting, role assignments - is marked `# not-testable:` with a reason, as for
storage. `ignore_changes` is a lifecycle rule, read from the code and not from a plan, so the
placeholder's guard is `not-testable` as well and named in the handover.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the vault this
way. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

An inline `access_policy` block and an `azurerm_key_vault_access_policy` fight on every apply;
with RBAC neither is used.
