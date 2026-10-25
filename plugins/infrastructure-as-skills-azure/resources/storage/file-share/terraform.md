# Rendering Azure Files shares as Terraform

Mapping from the question set to the shares. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

A share is a child of a storage account, and the AVM storage account module takes its shares as
an input. **There is no module call of its own:** the decisions below land in the `shares`
input of the account's call, rendered by [../storage-account/terraform.md](../storage-account/terraform.md).
Module: `Azure/avm-res-storage-storageaccount/azurerm` v0.10.0 (resolved 2026-10-25), pinned and
provider-constrained as there.

## With the AVM module

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `share_names` | `shares = { <key> = { name, quota } }` | `name` and `quota` are both **required** members |
| `protocol` | `shares.<k>.enabled_protocol` | `SMB` or `NFS`; default `null`; written. Fixed at creation |
| `quota_gb` | `shares.<k>.quota` | GB; the provisioned size on Premium |
| `access_tier` | `shares.<k>.access_tier` | `TransactionOptimized`, `Hot`, `Cool`, `Premium`; default `null` (the platform's); written |
| `root_squash` | `shares.<k>.root_squash` | NFS only |
| `role_assignments` | `shares.<k>.role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | SMB data roles |

```hcl
  # inside module "storage" - decision: file-share.shares.*
  shares = {
    for s in var.share_names : s => {
      name             = s
      quota            = 100
      enabled_protocol = "SMB"
      access_tier      = "TransactionOptimized"
    }
  }
```

### Tests

The share is a child of the account module; asserts target what the account module exposes at
plan time (read off a first `terraform test` on the pinned version), and what the plan hides is
marked `# not-testable:` with a reason, as for the account's other children.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_storage_share` |
|---|---|
| `share_names` | `name`, `storage_account_id` |
| `protocol` | `enabled_protocol` |
| `quota_gb` | `quota` (required) |
| `access_tier` | `access_tier` |
| `root_squash` | not on the resource; an `azapi_update_resource` on `Microsoft.Storage/storageAccounts/fileServices/shares` sets `rootSquash` |
| `role_assignments` | `azurerm_role_assignment` with `scope = azurerm_storage_share.<k>.rbac_scope_id` (**not** the resource id: the File service's role scope differs) |
