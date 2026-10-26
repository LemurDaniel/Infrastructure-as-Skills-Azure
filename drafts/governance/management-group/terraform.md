# Rendering a management group as Terraform

Mapping from the question set to the group, its subscriptions and its role assignments. General
layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/terraform-idiom.md).
Nothing here renders when `management_group_ownership` is `platform`.

## With the AVM module

**There is none published.** The Terraform index lists `avm-res-management-managementgroup` as
`Proposed` (looked up 2026-10-26) - no code, no registry entry - so the render is authored, with
`implementation: authored` and `source: forced`, `forced_by: no AVM module for
Microsoft.Management/managementGroups`. The hierarchy pattern `avm-ptn-alz` (v0.22.0 on the same
date) builds the ALZ groups and is named as the boundary, never called from this set. The Bicep side
has a resource module (see `bicep.md`).

## Authored rendering

Targets `azurerm` **5.x** (checked against `terraform providers schema -json`, 5.11.0). The
provider is configured for any subscription of the tenant; the group is a tenant-level resource
and the subscription on the provider only decides where the deployment's own calls are counted.

| Decision | Resource and argument |
|---|---|
| `group_id` | `azurerm_management_group.name` |
| `display_name` | `display_name` (omitted when empty; the provider then uses the name) |
| `parent` | `parent_management_group_id` - the full id `/providers/Microsoft.Management/managementGroups/<id>` |
| `subscriptions` | one `azurerm_management_group_subscription_association` per id, `subscription_id = "/subscriptions/<id>"`; never `subscription_ids` on the group as well |
| `role_assignments` | `azurerm_role_assignment` with `scope = azurerm_management_group.this.id`, through the `role-assignment` set's rendering |
| `management_group_ownership` | whether the resources exist at all |
| `environments` | one deployment from the platform's stage file, not one per stage |

```hcl
# decision: management-group.group.group_id - immutable, the name is the id
resource "azurerm_management_group" "this" {
  name = "mg-payments"
  # decision: management-group.group.display_name
  display_name = "Payments"
  # decision: management-group.placement.parent
  parent_management_group_id = var.parent_management_group_id
}

# decision: management-group.group.subscriptions - the association, never subscription_ids on the group
resource "azurerm_management_group_subscription_association" "this" {
  for_each            = toset(var.subscription_ids)
  management_group_id = azurerm_management_group.this.id
  subscription_id     = "/subscriptions/${each.value}"
}

# decision: management-group.identity.role_assignments - at the group's id
resource "azurerm_role_assignment" "readers" {
  scope                = azurerm_management_group.this.id
  role_definition_name = "Reader"
  principal_id         = var.platform_readers_group_id
  principal_type       = "Group"
}

output "management_group_id" { value = azurerm_management_group.this.id }
```

`var.parent_management_group_id` and `var.subscription_ids` come from the stage file. A root that
also assigns a policy at the new group (`policy` set) puts a `time_sleep` of about a minute between
`azurerm_management_group.this` and the assignment: the new scope is not authorised for the deploying
identity instantly.

### Tests

`mock_provider "azurerm"` keeps the plan credential-free. Every decision is observable:
`azurerm_management_group.this.name`, `display_name`, `parent_management_group_id`, the set of
`azurerm_management_group_subscription_association.this[*].subscription_id` (compared as JSON), and
the role assignment's `scope`, `role_definition_name` and `principal_type`.
`management_group_ownership` is `# not-testable:` as a check on the spec.
