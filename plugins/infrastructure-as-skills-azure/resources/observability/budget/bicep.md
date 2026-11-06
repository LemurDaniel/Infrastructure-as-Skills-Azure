# Rendering a budget as Bicep

Mapping from the question set to `Microsoft.Consumption/budgets`, deployed at resource group scope
into the group it watches. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/budget.bicep
```

## The AVM module, and why it is not called

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/consumption/budget/rg-scope:<version>` | **0.1.0** (child of the multi-scope `avm/res/consumption/budget` 0.3.8) | 2026-11-01 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. At 0.1.0 the module takes **one
`thresholdType` for every threshold**: actual and forecast notifications cannot share a budget,
and the default answers hold both (`actual_thresholds: [80, 100]`, `forecast_thresholds: [100]`).
Two budgets to work around it would double the names and the notifications in the portal. So the
budget renders authored, in both targets; a module version that takes the type per threshold
changes `modules.bicep` in render-map.yaml.

The module's `startDate` also defaults to `utcNow()` - a value that changes with every
deployment month. Wherever it is called, the start date is passed explicitly.

## Authored rendering

`Microsoft.Consumption/budgets@2024-08-01`. What each decision renders to - the property and the
literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it
for a spec.

Not decisions of this set:

| Decision | Property | Note |
|---|---|---|
| (the budget) | `name` | Assembled from the `budget` abbreviation, affix and workload |
| (the start) | `properties.timePeriod.startDate` | A param from each stage file: the first day of the month of the stage's first deployment, never `utcNow()` and never a literal in the template - see [notes.md](notes.md#fixed-at-creation) |
| (the end) | `properties.timePeriod.endDate` | Left out; the API sets it ten years ahead |
| (the kind) | `properties.category` | `'Cost'` |
| (the comparison) | `notifications.*.operator` | `'GreaterThanOrEqualTo'` |
| `context.tags` | - | A budget has no tags |

### The resource

```bicep
@description('First day of the month of the stage\'s first deployment - from the stage file, fixed')
param budgetStartDate string

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: budgetAmount // decision: budget.budget.amount - per stage, from the stage file
    timeGrain: 'Monthly' // decision: budget.budget.time_grain
    timePeriod: {
      startDate: budgetStartDate
    }
    // One key per threshold, written out - a toObject() over the list compiles to an
    // expression the ARM tests cannot read.
    notifications: {
      // decision: budget.budget.actual_thresholds
      actual_80: {
        enabled: true
        threshold: 80
        thresholdType: 'Actual'
        operator: 'GreaterThanOrEqualTo'
        contactGroups: [actionGroupId] // decision: budget.notifications.action_group
        contactEmails: [] // decision: budget.notifications.contact_emails
        contactRoles: ['Owner'] // decision: budget.notifications.contact_roles
      }
      actual_100: {
        enabled: true
        threshold: 100
        thresholdType: 'Actual'
        operator: 'GreaterThanOrEqualTo'
        contactGroups: [actionGroupId]
        contactEmails: []
        contactRoles: ['Owner']
      }
      // decision: budget.budget.forecast_thresholds
      forecast_100: {
        enabled: true
        threshold: 100
        thresholdType: 'Forecasted'
        operator: 'GreaterThanOrEqualTo'
        contactGroups: [actionGroupId]
        contactEmails: []
        contactRoles: ['Owner']
      }
    }
  }
}

output id string = budget.id
```

Validated with `bicep build`. A module that holds it is deployed with `scope:` the stage's
resource group - the scope is the decision `placement.resource_group_name`.

### Tests

One entry per decision in `tests/*.armtest.yaml` against the compiled ARM
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `amount` is the
stage parameter, `timeGrain` is `Monthly`, the keys `actual_80`, `actual_100` and `forecast_100`
exist with their `threshold` and `thresholdType`, and every notification carries the action
group, the role list and the e-mail list. At most five keys under `notifications`.
