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

What each decision renders to - the input and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Input | Note |
|---|---|---|
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
there is no call: `existing_plan` is `{ existing: ddos_protection_plan }` in the spec and renders as
an id variable from the stage files, which the networks take as it is - no data source and no
provider alias into the connectivity subscription ([terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md#referencing-what-the-deployment-does-not-own)):

```hcl
variable "ddos_protection_plan_id" {
  description = "The platform's DDoS protection plan (ddos-protection-plan.plan.existing_plan). From the stage file."
  type        = string

  validation {
    condition     = can(regex("^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.Network/ddosProtectionPlans/[^/]+$", var.ddos_protection_plan_id))
    error_message = "ddos_protection_plan_id must be the resource id of a DDoS protection plan."
  }
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

# not-testable: ddos-protection-plan.plan.ownership - decides whether the module or the id variable is rendered, which the root's wiring test sees
# not-testable: ddos-protection-plan.plan.existing_plan - an id variable under platform; the variable's validation checks its type
# not-testable: ddos-protection-plan.plan.stages_with_plan - the module's count per stage file; the non-production run asserts count 0
# not-testable: ddos-protection-plan.access.role_assignments - inside the module
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Resource / argument |
|---|---|
| the plan | `azurerm_network_ddos_protection_plan` (`name`, `location`, `resource_group_name`, `tags`); `virtual_network_ids` is read-only |
| the association | **not here**: `azurerm_virtual_network.ddos_protection_plan { id, enable }` in the network's render |

Validated against `azurerm` 5.x.
