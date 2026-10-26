# Rendering a DDoS protection plan as Bicep

Mapping from the question set to `Microsoft.Network/ddosProtectionPlans`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/ddos-protection-plan.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/ddos-protection-plan:<version>` | **0.3.2** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `ownership: platform` | - | The module is **not called**; an `existing` resource with `scope: resourceGroup(subscriptionId, resourceGroupName)` reads `existing_plan` and its `id` goes to the networks |
| `ownership: deployment` | the call below | |
| `stages_with_plan` | a `param ddosProtectionPlanEnabled bool` and `if (ddosProtectionPlanEnabled)` on the module | `true` in `main.production.bicepparam` only |
| `location` | `location` | Module default is the group's location; written |
| `resource_group_name` | the deployment's scope | |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName: 'Network Contributor', principalType } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set. `lock` is a parameter the question set
has no decision for - leave it unset.

### The call

```bicep
// decision: ddos-protection-plan.plan.ownership - deployment: the plan is created here
module ddosProtectionPlan 'br/public:avm/res/network/ddos-protection-plan:0.3.2' = {
  name: 'ddos-protection-plan'
  params: {
    name: ddosPlanName
    location: location
    tags: tags

    // decision: ddos-protection-plan.access.role_assignments
    roleAssignments: []

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = ddosProtectionPlan.outputs.resourceId // virtual-network.ddos_protection takes it
```

Validated with `bicep build` against the published module. For `ownership: platform` the call is
replaced by a reference into the connectivity subscription:

```bicep
resource platformDdosPlan 'Microsoft.Network/ddosProtectionPlans@2024-05-01' existing = {
  name: ddosProtectionPlanName
  scope: resourceGroup(connectivitySubscriptionId, ddosProtectionPlanResourceGroupName)
}
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so `name`, `location`, `roleAssignments` and `enableTelemetry` are observable in
`tests/*.armtest.yaml` ([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests));
`stages_with_plan` is the module's `condition` expression, matched on its text; `ownership` and
`existing_plan` are the presence of the module or of the `existing` reference and are asserted as
that.

## Authored rendering

The fallback. `Microsoft.Network/ddosProtectionPlans` with `location`, `tags` and an empty
`properties: {}`; role assignments as extension resources with `scope`. The association is
`properties.enableDdosProtection: true` and `properties.ddosProtectionPlan: { id }` on the virtual
network, in its own render. Validated with `bicep build`.
