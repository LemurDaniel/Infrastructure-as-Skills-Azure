# Rendering a budget as Terraform

Mapping from the question set to the resource group budget. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## No AVM module

| Module | Status | Resolved |
|---|---|---|
| `Azure/avm-res-consumption-budget/azurerm` | Does not exist (no repository, no registry entry) | 2026-11-01 |

Resolve again before rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says;
until a module exists the budget renders authored.

## Authored rendering

`azurerm_consumption_budget_resource_group`. Targets `azurerm` **5.x**; check against
`terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Argument | Note |
|---|---|---|
| (the budget) | `name` through the naming provider | `budget-gwc-dev-telemetry-01` |
| (the start) | `time_period.start_date` | `formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())` with `ignore_changes = [time_period]`: ForceNew, and it may not lie in a past month at create - see [notes.md](notes.md#fixed-at-creation) |
| (the end) | `time_period.end_date` | Left out; the API sets it ten years ahead |
| (the comparison) | `notification.operator` | `GreaterThanOrEqualTo` - 100 % notifies at the amount, not one cent after |
| `context.tags` | - | A budget has no tags |

### The resource

```hcl
data "naming_name" "budget" {
  resource = "Azure::Microsoft.Consumption/budgets"
}

locals {
  # decision: budget.notifications.action_group, contact_emails, contact_roles - in every notification
  budget_contacts = {
    contact_groups = [var.action_group_id]
    contact_emails = []
    contact_roles  = ["Owner"]
  }
  budget_notifications = merge(
    # decision: budget.budget.actual_thresholds
    { for t in [80, 100] : "actual_${t}" => { threshold = t, threshold_type = "Actual" } },
    # decision: budget.budget.forecast_thresholds
    { for t in [100] : "forecast_${t}" => { threshold = t, threshold_type = "Forecasted" } },
  )
}

resource "azurerm_consumption_budget_resource_group" "this" {
  name              = data.naming_name.budget.name
  resource_group_id = var.resource_group_id # an id, not a name
  amount            = var.budget_amount     # decision: budget.budget.amount - per stage
  time_grain        = "Monthly"             # decision: budget.budget.time_grain

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  dynamic "notification" {
    for_each = local.budget_notifications
    content {
      enabled        = true
      threshold      = notification.value.threshold
      threshold_type = notification.value.threshold_type
      operator       = "GreaterThanOrEqualTo"
      contact_groups = local.budget_contacts.contact_groups
      contact_emails = local.budget_contacts.contact_emails
      contact_roles  = local.budget_contacts.contact_roles
    }
  }

  lifecycle {
    ignore_changes = [time_period] # the start is fixed at create; a new month must not replace it
  }
}

output "id" { value = azurerm_consumption_budget_resource_group.this.id }
```

`var.resource_group_id` is the stage's group id - the AVM resource group module's `resource_id`
where the render creates the group, a stage-file variable where it exists. Validated with
`terraform validate` against `azurerm` 5.12.

### Tests

`mock_provider "azurerm"`; the naming provider stays real. Every decision is an argument of the
resource, so every one is observable at plan. `notification` is a set: compare through `tolist`
and filter by `threshold_type`, never by index. Settled by a `terraform test` run on `azurerm`
5.12:

```hcl
run "budget" {
  command = plan

  # decision: budget.budget.amount
  assert {
    condition     = azurerm_consumption_budget_resource_group.this.amount == var.budget_amount
    error_message = "The amount comes from the stage file."
  }

  # decision: budget.budget.time_grain
  assert {
    condition     = azurerm_consumption_budget_resource_group.this.time_grain == "Monthly"
    error_message = "Counted per month, like the invoice."
  }

  # decision: budget.budget.actual_thresholds
  assert {
    condition     = sort([for n in azurerm_consumption_budget_resource_group.this.notification : tostring(n.threshold) if n.threshold_type == "Actual"]) == tolist(["100", "80"])
    error_message = "Actual notifications at 80 and 100 percent."
  }

  # decision: budget.budget.forecast_thresholds
  assert {
    condition     = sort([for n in azurerm_consumption_budget_resource_group.this.notification : tostring(n.threshold) if n.threshold_type == "Forecasted"]) == tolist(["100"])
    error_message = "A forecast notification at 100 percent."
  }

  # decision: budget.notifications.action_group
  # decision: budget.notifications.contact_emails
  # decision: budget.notifications.contact_roles
  assert {
    condition     = alltrue([for n in azurerm_consumption_budget_resource_group.this.notification : tolist(n.contact_groups) == tolist([var.action_group_id]) && tolist(n.contact_roles) == tolist(["Owner"]) && length(n.contact_emails) == 0])
    error_message = "Every notification reaches the action group and the owners."
  }

  # decision: budget.placement.resource_group_name
  assert {
    condition     = azurerm_consumption_budget_resource_group.this.resource_group_id == var.resource_group_id
    error_message = "The budget watches the stage's resource group."
  }
}
```

`sort` orders strings, so `"100"` comes before `"80"`.
