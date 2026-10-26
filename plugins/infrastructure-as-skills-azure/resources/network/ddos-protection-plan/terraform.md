# Rendering a DDoS protection plan as Terraform

Mapping from the question set to the plan. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-ddosprotectionplan/azurerm` | **v0.3.0** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**`azurerm`-based**: it takes `resource_group_name` (a name) and requires
`azurerm >= 3.116, < 5.0`, `modtm ~> 0.3`, `random ~> 3.5`, Terraform `>= 1.6` - a root calling it
cannot be on `azurerm` 5.x. No `azapi`. The root's provider set is the union with the other
modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `ownership: platform` | - | The module is **not called**; a `data "azurerm_network_ddos_protection_plan"` reads `existing_plan` and its `id` goes to the networks |
| `ownership: deployment` | the call below | |
| `existing_plan` | `data "azurerm_network_ddos_protection_plan" { name, resource_group_name }` with a provider alias for the connectivity subscription | Under `platform` only |
| `stages_with_plan` | `count` on the module / data source per stage | `production`: the module in the production root's stage file only; the other stages' networks render `ddos_protection = false` |
| `location` | `location` | Required by the module |
| `resource_group_name` | `resource_group_name` | A name, not an id |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | `"Network Contributor"` or `"Reader"` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.3.0: nothing from this question set. `lock` is an input the question
set has no decision for (`deployment.resource_lock` does not list the plan) - leave it `null`.

### The call

```hcl
data "naming_name" "ddos_protection_plan" {
  resource = "Azure::Microsoft.Network/ddosProtectionPlans"
}

# decision: ddos-protection-plan.plan.ownership - deployment: the plan is created here
module "ddos_protection_plan" {
  source  = "Azure/avm-res-network-ddosprotectionplan/azurerm"
  version = "~> 0.3.0"

  name                = data.naming_name.ddos_protection_plan.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: ddos-protection-plan.access.role_assignments
  role_assignments = {}
  lock             = null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.ddos_protection_plan.resource_id } # virtual-network.ddos_protection takes it
```

Validated with `terraform validate` (registry, v0.3.0, `azurerm ~> 4.0`). For `ownership: platform`
the call is replaced by the data source, in the connectivity subscription through a provider alias:

```hcl
data "azurerm_network_ddos_protection_plan" "platform" {
  provider            = azurerm.connectivity
  name                = var.ddos_protection_plan.name
  resource_group_name = var.ddos_protection_plan.resource_group_name
}
```

`stages_with_plan: production` puts a `count = var.ddos_protection_plan_enabled ? 1 : 0` on the
module, `true` in `environments/production.tfvars` only; the networks of the other stages take
`ddos_protection_plan = null`.

### Tests

`mock_provider "azurerm"`, `"modtm"` and `"random"`; the naming provider stays real. The module
exposes `name`, `resource_id` and a `resource` output that is the `azurerm_network_ddos_protection_plan`
itself, so the plan observes `name`, `location` and `resource_group_name`; `resource_id` is
unknown at plan. Settled by a `terraform test` run on v0.3.0:

```hcl
run "plan" {
  command = plan

  assert {
    condition     = module.ddos_protection_plan.resource.name == "ddos-gwc-prod-platform-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
  assert {
    condition     = module.ddos_protection_plan.resource.location == var.location
    error_message = "The plan is placed in the context's region."
  }
}

# not-testable: ddos-protection-plan.plan.ownership - decides whether the module or the data source is rendered, which the root's wiring test sees
# not-testable: ddos-protection-plan.plan.existing_plan - a data source under platform; not in a deployment root
# not-testable: ddos-protection-plan.plan.stages_with_plan - the module's count per stage file; the non-production run asserts count 0
# not-testable: ddos-protection-plan.access.role_assignments - inside the module
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource / argument |
|---|---|
| the plan | `azurerm_network_ddos_protection_plan` (`name`, `location`, `resource_group_name`, `tags`); `virtual_network_ids` is read-only |
| `existing_plan` | `data "azurerm_network_ddos_protection_plan"` |
| `role_assignments` | `azurerm_role_assignment` on the plan's id |
| the association | **not here**: `azurerm_virtual_network.ddos_protection_plan { id, enable }` in the network's render |

Validated against `azurerm` 5.x.
