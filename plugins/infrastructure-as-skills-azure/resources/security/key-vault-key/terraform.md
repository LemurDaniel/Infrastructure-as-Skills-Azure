# Rendering a Key Vault key as Terraform

Mapping from the question set to the key. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-keyvault-vault/azurerm//modules/key` | **v0.12.0** | 2026-10-25 | **Orphaned** in the index (it is the vault module's submodule) |

Resolve the current version and re-read the submodule's README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.12.0`, the same as the
vault's. There is no module of its own in the index: the key is a **submodule of the Key Vault
module**, called with a `//modules/key` suffix, so it carries that module's `Orphaned` status - say so
in the handover. It is `azurerm`-based (`azurerm >= 4.81, < 5.0`, Terraform `>= 1.9`) and
needs no further provider: **a root calling it cannot be on 5.x**. The same module's `keys` input
(used by the `key-vault` set for its customer-managed keys) takes the same members.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Decision | Input | Note |
|---|---|---|
| name | `name` | From the naming interface |
| `context.tags` | `tags` | `map(string)` |
| `deployment.module_telemetry` | *none* | The submodule has no telemetry input |

### The call

```hcl
module "key" {
  source  = "Azure/avm-res-keyvault-vault/azurerm//modules/key"
  version = "~> 0.12.0"

  key_vault_resource_id = module.vault.resource_id
  name                  = "key-storage-cmk"

  # decision: key-vault-key.security.algorithm / protection - RSA, software
  type = "RSA"
  # decision: key-vault-key.security.key_size
  size = 3072
  # decision: key-vault-key.security.key_operations - the submodule default is none
  opts = ["wrapKey", "unwrapKey"]

  # decision: key-vault-key.data_protection.rotation_days / expiry_days / notify_days_before_expiry
  rotation_policy = {
    automatic = {
      time_after_creation = "P90D"
    }
    expire_after         = "P365D"
    notify_before_expiry = "P30D"
  }

  # decision: key-vault-key.identity.role_assignments
  role_assignments = {
    storage = {
      role_definition_id_or_name = "Key Vault Crypto Service Encryption User"
      principal_id               = module.identity.principal_id
      principal_type             = "ServicePrincipal"
    }
  }

  tags = local.tags
}

output "key_versionless_id" { value = module.key.resource_versionless_id }
output "key_id" { value = module.key.resource_id }
```

Outputs include `id`, `resource_id`, `resource_versionless_id`, `versionless_id`, `name`, the
public key and the RSA/EC components; the consumer takes `resource_versionless_id`. Output names
are read from the README of the pinned version.

The first version of the key is created before the rotation policy applies, and the module sets
no `expiration_date` on it: `expiry_days` dates the versions that rotation creates. A first version
that must itself expire is a departure the module cannot express, and is rendered authored.

### Tests

`mock_provider "azurerm"` keeps the plan credential-free. The submodule is one `azurerm_key_vault_key`
plus its role assignments, so asserts target `module.key.azurerm_key_vault_key.this`: `key_type`,
`key_size`, `key_opts`, the rotation policy (its `automatic` and `expire_after` blocks). The role
assignments are asserted on `module.key.azurerm_role_assignment.this["<k>"]` where the plan shows
them; the exact addresses are read off a first `terraform test` run on the pinned version, not
recalled. A near-expiry subscription is `# not-testable:`.

## Authored rendering

The fallback - `implementation: authored`, a root on `azurerm` **5.x**, or a repository that
renders keys this way. Checked against `terraform providers schema -json` (5.11.0).

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Argument on `azurerm_key_vault_key` |
|---|---|
| first version expiry | `expiration_date` (an RFC 3339 date; a `time_offset` resource gives one that does not move on every plan) |

```hcl
resource "azurerm_key_vault_key" "this" {
  name         = "key-storage-cmk"
  key_vault_id = module.vault.resource_id
  key_type     = "RSA"
  key_size     = 3072
  key_opts     = ["wrapKey", "unwrapKey"]

  rotation_policy {
    automatic {
      time_after_creation = "P90D"
    }
    expire_after         = "P365D"
    notify_before_expiry = "P30D"
  }
}
```
