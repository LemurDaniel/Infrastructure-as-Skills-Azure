# Rendering a subscription (vending) as Terraform

Mapping from the question set to the alias, its placement, providers and access. General layout,
variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
Nothing here renders when `subscription_ownership` is `platform`.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/lz-vending/azurerm` | **v7.0.3** | 2026-10-26 | Available (pattern; indexed as `avm-ptn-alz-sub-vending`, "Azure Landing Zones - Sub vending") |

The index names `avm-ptn-alz-sub-vending`, whose repository is not published; the registry
coordinate that exists is `Azure/lz-vending/azurerm`, and the index's alternative name says they
are the same module. Resolve the current version and re-read the README inputs before rendering,
as [avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 7.0` - the module
is past 1.0, so the major is the pin.

**AzAPI only**: it requires `azapi ~> 2.5`, `time ~> 0.9` and Terraform `~> 1.10`, and **no
`azurerm`** - it sits in a root on 4.x or 5.x. The root's `azapi` provider is configured without a
subscription (there is none yet); `azurerm` is still needed for an authored role assignment or a
data source on the result. The module is instantiated once per subscription; a stack renders one
call per stage from the stage file.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `subscription_ownership: deployment` | `subscription_alias_enabled = true` | `false` with `subscription_id` would only manage an existing one; not this set's case |
| `billing_scope` | `subscription_billing_scope` | EA / MCA / MPA id, case sensitive |
| `workload_type` | `subscription_workload` | `"Production"` / `"DevTest"` |
| `alias_name` | `subscription_alias_name` | Generated `sub-<workload>-<stage>` when empty |
| `display_name` | `subscription_display_name` | The alias when empty |
| `context.tags` | `subscription_tags` | |
| `management_group` | `subscription_management_group_id` + `subscription_management_group_association_enabled = true` | The id alone |
| `register_resource_providers` | `subscription_register_resource_providers_enabled` + `subscription_register_resource_providers_and_features = { "<ns>" = [] }` | Module default is **disabled**; `false` and `{}` when the list is empty |
| `role_assignments` | `role_assignment_enabled = true` + `role_assignments = { <k> = { principal_id, definition, relative_scope = "" } }` | `definition` a built-in name or a definition id |
| `location` | `location` | Required by the module |
| `cancel_on_removal` | *not carried* - the module cancels on destroy; a handover line | |
| boundaries | `virtual_network_enabled = false`, `budget_enabled = false`, `umi_enabled = false`, `resource_group_creation_enabled = false`, `network_security_group_enabled = false`, `route_table_enabled = false` | Written so a reader sees the pattern's other capabilities were declined |
| `deployment.module_telemetry` | `disable_telemetry` | **Inverted**: `disable_telemetry = true` for `disabled` |

### The call

```hcl
module "subscription" {
  source  = "Azure/lz-vending/azurerm"
  version = "~> 7.0"

  location = var.location

  # decision: subscription.placement.subscription_ownership - deployment: the alias is created
  subscription_alias_enabled = true
  # decision: subscription.billing.billing_scope
  subscription_billing_scope = var.billing_scope
  # decision: subscription.billing.workload_type - DevTest outside production
  subscription_workload = var.subscription_workload
  # decision: subscription.billing.alias_name / display_name - generated from workload and stage
  subscription_alias_name   = "sub-${var.workload}-${var.environment}"
  subscription_display_name = "sub-${var.workload}-${var.environment}"
  subscription_tags         = local.tags

  # decision: subscription.placement.management_group
  subscription_management_group_association_enabled = true
  subscription_management_group_id                  = var.management_group_id

  # decision: subscription.service.register_resource_providers - the module default is none
  subscription_register_resource_providers_enabled      = true
  subscription_register_resource_providers_and_features = {
    "Microsoft.Storage" = []
    "Microsoft.Web"     = []
  }

  # decision: subscription.identity.role_assignments
  role_assignment_enabled = true
  role_assignments = {
    team_owners = {
      principal_id   = var.team_owners_group_id
      definition     = "Owner"
      relative_scope = ""
    }
  }

  # not rendered here: network, budget, identities and resource groups come from their own sets
  virtual_network_enabled         = false
  budget_enabled                  = false
  umi_enabled                     = false
  resource_group_creation_enabled = false

  # decision: deployment.module_telemetry - inverted switch
  disable_telemetry = true
}

output "subscription_id" { value = module.subscription.subscription_id }
```

Outputs are `subscription_id`, `subscription_resource_id`,
`management_group_subscription_association_id` and the ids of the declined capabilities (empty).
The subscription id output is what the workload's stage file receives; the handover says so.

### Tests

`mock_provider "azapi"` and `mock_provider "time"` keep the plan credential-free. The alias is an
`azapi_resource` in the module's `subscription` child (`module.subscription.module.subscription[0]`
- the address is read off a first `terraform test` run on the pinned version), and its `body`
carries `properties.billingScope`, `workload`, `displayName` and `additionalProperties.tags`;
the association and the role assignments are `azapi_resource`s whose `parent_id` is unknown at plan
time (the new subscription), so `management_group`, `role_assignments` and
`register_resource_providers` are `# not-testable:` with that reason, and `cancel_on_removal` is a
handover line.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the alias this way.
Targets `azurerm` **5.x** (checked against `terraform providers schema -json`, 5.11.0). The provider
needs a subscription to be configured with (any of the tenant's); the alias is a tenant resource.

| Decision | Resource and argument |
|---|---|
| `alias_name`, `display_name`, `billing_scope`, `workload_type`, `context.tags` | `azurerm_subscription`: `alias`, `subscription_name`, `billing_scope_id`, `workload`, `tags` |
| `management_group` | `azurerm_management_group_subscription_association` with `subscription_id = "/subscriptions/${azurerm_subscription.this.subscription_id}"` |
| `register_resource_providers` | `azurerm_resource_provider_registration` per namespace, through a provider alias configured for the new subscription (a second `apply`, since a provider cannot be configured with an unknown id) |
| `role_assignments` | `azurerm_role_assignment` with `scope = "/subscriptions/<id>"`, through the `role-assignment` set |
| `cancel_on_removal: false` | `lifecycle { prevent_destroy = true }` and `features { subscription { prevent_cancellation_on_destroy = true } }` on the provider |

```hcl
provider "azurerm" {
  features {
    subscription {
      # decision: subscription.data_protection.cancel_on_removal
      prevent_cancellation_on_destroy = true
    }
  }
}

# decision: subscription.billing.* - the alias
resource "azurerm_subscription" "this" {
  alias             = "sub-${var.workload}-${var.environment}"
  subscription_name = "sub-${var.workload}-${var.environment}"
  billing_scope_id  = var.billing_scope
  workload          = var.subscription_workload
  tags              = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

# decision: subscription.placement.management_group
resource "azurerm_management_group_subscription_association" "this" {
  management_group_id = var.management_group_id
  subscription_id     = "/subscriptions/${azurerm_subscription.this.subscription_id}"
}
```

The authored plan observes every alias attribute and the association's `management_group_id`;
`register_resource_providers` is `# not-testable:` until the second apply configures the provider.
