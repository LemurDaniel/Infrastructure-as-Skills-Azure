# Rendering a role assignment as Terraform

Mapping from the question set to a standalone assignment. General layout, variables and tagging are
in [../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
Which assignments come here and which go through a module's `role_assignments` interface is
decided in [notes.md](notes.md#interface-or-standalone).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-authorization-roleassignment/azurerm` | **v0.3.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**It is a utility module, not a resource module.** It takes maps of principals and assignments
for every scope kind (Azure Resource Manager and Entra ID), computes the lookups, and creates the
`azurerm_role_assignment`s; it has no `name`, no `location`, no `tags`, and its `resource_id`
output is `null`. It requires `azurerm >= 4.81, < 5.0` through its own constraint set -
**a root calling it cannot be on 5.x** - plus `azapi ~> 2.12`, `azuread >= 2.46, < 4.0`,
`modtm ~> 0.3`, `random ~> 3.5`, Terraform `~> 1.6`. The `azuread` provider is required even when
no Entra ID input is used; the root carries it in its provider set (unconfigured, it is never
called) and the tests mock it. One call per deployment with every standalone assignment of the spec as
an entry is the normal shape.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `scope` (any `scope_kind`) | `role_assignments_azure_resource_manager.<k>.scope` | A resource id, a group id, `/subscriptions/<id>` or `/providers/Microsoft.Management/managementGroups/<name>`. The module does not check that it exists |
| `principal` | `...<k>.principal_id` | An object id; from the identity module's `principal_id` output |
| `principal_type` | `...<k>.principal_type` | **`ServicePrincipal`** for a managed identity. The module's own `User`, `Group`, `ServicePrincipal` values pass through; its docs also list `SystemAssignedManagedIdentity` and `UserAssignedManagedIdentity`, which it uses for its helper maps and are not passed to Azure - check the README of the version pinned |
| `role` | `...<k>.role_definition_name` | By name. `role_definition_id` for a role the name table does not resolve |
| `condition` | `...<k>.condition` | `null` when empty |
| (set with a condition) | `...<k>.condition_version` | `"2.0"`, always beside a condition; `null` otherwise |
| `description` | `...<k>.description` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `deployer_role` | *none* | Not in the template; the handover (see `notes.md`) |

### The call

```hcl
module "role_assignments" {
  source  = "Azure/avm-res-authorization-roleassignment/azurerm"
  version = "~> 0.3.0"

  role_assignments_azure_resource_manager = {
    # decision: role-assignment.identity.role / principal - the app's identity on the vault's secret
    app_secrets_user = {
      scope                = module.vault.resource_id
      principal_id         = module.identity.principal_id
      # decision: role-assignment.identity.principal_type - a managed identity is a ServicePrincipal
      principal_type       = "ServicePrincipal"
      role_definition_name = "Key Vault Secrets User"
      # decision: role-assignment.security.condition
      condition         = null
      condition_version = null
      description       = "The app reads its secrets"
    }
  }

  enable_telemetry = true
}

output "role_assignments" { value = module.role_assignments.role_assignments }
```

The output is a map keyed like the input, each value `{ role_definition_id, principal_id, scope }`.
Output names are read from the README of the pinned version. A key is the stable address of the
assignment: it is the decision's own key (`<consumer>_<role>`), never an index.

### Ordering and waiting

The module creates the assignments in one pass. When a data-plane write follows (a key or a
secret created by the same root), depend on the module's output and add a `time_sleep` of about a
minute after it - the propagation delay is the platform's, and the Key Vault module's own
`wait_for_rbac_before_*` covers only its own assignments.

### Tests

`mock_provider "azurerm"` (and `azapi`, `azuread`, `modtm`) keep the plan credential-free. The
module hides each assignment in a nested resource, so an assert targets the module's `role_assignments`
output where the plan knows it (the scope, the principal id) and the `azurerm_role_assignment`
instance addressed `module.role_assignments.azurerm_role_assignment.<...>` for the role name,
principal type and condition - the exact addresses are read off a first `terraform test` run on
the pinned version, not recalled. `deployer_role` is `# not-testable:` - it is a right of the
pipeline, not an attribute of the plan.

## Authored rendering

The fallback - `implementation: authored`, a root that must be on `azurerm` 5.x, or a repository
that already renders assignments this way. Targets `azurerm` **5.x**; checked against
`terraform providers schema -json` (5.11.0).

| Decision | Argument on `azurerm_role_assignment` |
|---|---|
| name | `name = uuidv5("url", "<scope>/<principal>/<role>")` - stable, derived from the triple; omit it to let the provider generate one, which is fine until an assignment is adopted by hand |
| `scope` | `scope` |
| `principal` | `principal_id` |
| `principal_type` | `principal_type` |
| `role` | `role_definition_name` (or `role_definition_id` - exclusive with the name) |
| `condition` | `condition`, with `condition_version = "2.0"` |
| `description` | `description` |

```hcl
resource "azurerm_role_assignment" "this" {
  for_each = local.role_assignments

  scope                = each.value.scope
  principal_id         = each.value.principal_id
  principal_type       = each.value.principal_type
  role_definition_name = each.value.role
  condition            = each.value.condition
  condition_version    = each.value.condition == null ? null : "2.0"
  description          = each.value.description
}
```

`skip_service_principal_aad_check` is not set: with a `principal_type` the lookup is skipped.
`delegated_managed_identity_resource_id` is cross-tenant and not covered.
