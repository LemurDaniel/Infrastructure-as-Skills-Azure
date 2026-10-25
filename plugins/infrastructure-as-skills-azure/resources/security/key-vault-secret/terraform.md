# Rendering a Key Vault secret as Terraform

Mapping from the question set to the secret. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-keyvault-vault/azurerm//modules/secret` | **v0.12.0** | 2026-10-25 | **Orphaned** in the index (it is the vault module's submodule) |

Resolve the current version and re-read the submodule's README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.12.0`, the same as the
vault's. Like the key, it is a **submodule of the Key Vault module** and carries its `Orphaned` status.
It is `azurerm`-based (`azurerm >= 4.81, < 5.0`, Terraform `>= 1.11`) and needs no further provider:
**a root calling it cannot be on 5.x**.

**The module is used for `value_source: secure_input` only.** It writes the value it is given and
has no guard for a value somebody else set; a placeholder is rendered authored (below).

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `key_vault` | `key_vault_resource_id` | The vault module's `resource_id` |
| name | `name` | |
| `content_type` | `content_type` | |
| `expiry_days` | `expiration_date` | A UTC datetime (`2026-11-01T00:00:00Z`) computed once from `time_offset` - see below |
| `value_source: secure_input` | `value_wo` + `value_wo_version` | **Write-only and ephemeral**: the root variable is `ephemeral = true`. `value` (stored in state) is not used. Raise `value_wo_version` to write a new version |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | Scoped to the secret's versionless id |
| `context.tags` | `tags` | `map(string)` |

### The call - a secure input

```hcl
variable "db_connection" {
  type      = string
  sensitive = true
  ephemeral = true
}

# The expiry is computed once, when the resource is created, and does not move on later plans.
resource "time_offset" "db_connection" {
  offset_days = 365
}

module "secret_db_connection" {
  source  = "Azure/avm-res-keyvault-vault/azurerm//modules/secret"
  version = "~> 0.12.0"

  key_vault_resource_id = module.vault.resource_id
  name                  = "db-connection"

  # decision: key-vault-secret.security.content_type
  content_type = "connection-string"
  # decision: key-vault-secret.security.expiry_days
  expiration_date = time_offset.db_connection.rfc3339
  # decision: key-vault-secret.security.value_source - secure_input; write-only, not in state
  value_wo         = var.db_connection
  value_wo_version = 1

  # decision: key-vault-secret.identity.role_assignments
  role_assignments = {
    app = {
      role_definition_id_or_name = "Key Vault Secrets User"
      principal_id               = module.identity.principal_id
      principal_type             = "ServicePrincipal"
    }
  }

  tags = local.tags
}

output "secret_uri" { value = module.secret_db_connection.resource_versionless_id }
```

Outputs are `id`, `name`, `resource_id`, `resource_versionless_id`, `versionless_id`; the consumer
takes the versionless one. Output names are read from the README of the pinned version.

### The call - a placeholder

Outside the module, so the value can be ignored. The identity that applies must be a writer on the
vault, and the vault reachable (see `key-vault/notes.md`). The same guard as the vault's slots,
with the expiry and content type this set decides:

```hcl
resource "time_offset" "placeholder" {
  for_each    = toset(var.secret_placeholders)
  offset_days = 365
}

resource "azurerm_key_vault_secret" "placeholder" {
  for_each = toset(var.secret_placeholders)

  name         = each.key
  key_vault_id = module.vault.resource_id
  value        = "placeholder - replace after deployment"
  content_type = "text/plain"
  # decision: key-vault-secret.security.expiry_days - the first version only
  expiration_date = time_offset.placeholder[each.key].rfc3339

  lifecycle {
    ignore_changes = [value, tags, expiration_date]
  }
}
```

`expiration_date` is in `ignore_changes` so a version somebody wrote is not given the placeholder's
date back; it is the one place the expiry is deliberately left to the process.
Role assignments on a placeholder are separate `azurerm_role_assignment`s scoped to
`azurerm_key_vault_secret.placeholder[<k>].resource_versionless_id`.

### Tests

`mock_provider "azurerm"` (and `time`) keep the plan credential-free. Asserts target
`module.secret_db_connection.azurerm_key_vault_secret.this` (`content_type`, `expiration_date` is
set) and `azurerm_key_vault_secret.placeholder["<name>"]` (`content_type`, the dummy value). What
the plan cannot observe is `# not-testable:` with a reason: `ignore_changes` is a lifecycle rule,
read from the code and not from a plan; the write-only value is never in the plan by design.

## Authored rendering

The fallback - `implementation: authored`, a root on `azurerm` **5.x**, or a repository that renders
secrets this way. Checked against `terraform providers schema -json` (5.11.0).

| Decision | Argument on `azurerm_key_vault_secret` |
|---|---|
| `content_type` | `content_type` |
| `expiry_days` | `expiration_date` |
| `value_source: secure_input` | `value_wo` + `value_wo_version` (ephemeral input) |
| `value_source: placeholder` | `value` as above, with `lifecycle { ignore_changes = [value, tags, expiration_date] }` |
| `role_assignments` | `azurerm_role_assignment`, `scope = ...resource_versionless_id` |

The placeholder block above is already the authored form, and is the one used with the AVM module
for the vault.
