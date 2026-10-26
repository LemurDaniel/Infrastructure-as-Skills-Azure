# Rendering a management group as Bicep

Mapping from the question set to the group, its subscriptions and its role assignments. General
layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/bicep-idiom.md).
Nothing here renders when `management_group_ownership` is `platform`.

```bash
bicep build --stdout main.management-group.bicep
```

The template's `targetScope` is `managementGroup` - the **parent** group, deployed with
`az deployment mg create --management-group-id <parent>`.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `br/public:avm/res/management/management-group:<version>` | **0.2.0** | 2026-10-26 | Available |
| `br/public:avm/ptn/mgmt-groups/subscription-placement:<version>` | **0.3.0** | 2026-10-26 | Available (pattern) |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/avm.md) says. Pin the exact version. The
hierarchy pattern `avm/ptn/alz/empty` is the boundary and is never called from here.

**Two scopes.** The resource module deploys at `managementGroup` scope (its `parentId` defaults
to the deployment's group); the placement pattern deploys at `tenant` scope, which from the same
template is `scope: tenant()`. `bicep build` refuses the other way round.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `group_id` | `name` | |
| `display_name` | `displayName` | Omitted when empty; the module falls back to the id |
| `parent` | `parentId` | The id alone, not the resource id; module default is the deployment's group - written anyway |
| `location` (none in the set) | `location` | Deployment metadata only; the deployment's location |
| `subscriptions` | placement module `parSubscriptionPlacement: [ { managementGroupId, subscriptionIds } ]` | Guids; `managementGroupId` is the new group's `outputs.name` |
| `role_assignments` | *not carried by the resource module* | Authored `Microsoft.Authorization/roleAssignments` in a module scoped to the new group (`scope: managementGroup(<id>)`), or the `role-assignment` set's pattern module |
| `deployment.module_telemetry` | `enableTelemetry` on both calls | |
| `management_group_ownership` | *the calls that exist* | |

### The call

```bicep
targetScope = 'managementGroup'

param location string
param parentId string
param subscriptionIds array
param enableTelemetry bool = false

module mg 'br/public:avm/res/management/management-group:0.2.0' = {
  name: 'mg-payments'
  params: {
    // decision: management-group.group.group_id - immutable
    name: 'mg-payments'
    // decision: management-group.group.display_name
    displayName: 'Payments'
    // decision: management-group.placement.parent - the id, not the resource id
    parentId: parentId
    location: location
    enableTelemetry: enableTelemetry
  }
}

// decision: management-group.group.subscriptions - tenant scope from the parent's deployment
module placement 'br/public:avm/ptn/mgmt-groups/subscription-placement:0.3.0' = {
  name: 'mg-payments-subscriptions'
  scope: tenant()
  params: {
    parSubscriptionPlacement: [
      {
        managementGroupId: mg.outputs.name
        subscriptionIds: subscriptionIds
      }
    ]
    location: location
    enableTelemetry: enableTelemetry
  }
}

output managementGroupId string = mg.outputs.resourceId
```

The call was built with `bicep build` against the versions in the table. Outputs of the resource
module are `name` and `resourceId`; of the placement module `subscriptionPlacementSummary`. The
role assignments at the new group are a second, small module deployed at the new group
(`scope: managementGroup('mg-payments')`) after it exists, as the `role-assignment` set renders them;
in the same template the module symbol must not be named `managementGroup`, which shadows the
scope function.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so `name`, `displayName`, `parentId` and the placement's `parSubscriptionPlacement` are
observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/bicep-idiom.md#tests)).
`management_group_ownership` is `not-testable` as a check on the spec.

## Authored rendering

The fallback, at `tenant` scope - a group is a tenant resource, and the authored form can create
it from `/` with its parent in `properties.details.parent`:

```bicep
targetScope = 'tenant'

param parentId string

resource mg 'Microsoft.Management/managementGroups@2023-04-01' = {
  name: 'mg-payments'
  properties: {
    displayName: 'Payments'
    details: {
      parent: { id: tenantResourceId('Microsoft.Management/managementGroups', parentId) }
    }
  }
}

// decision: management-group.group.subscriptions
resource member 'Microsoft.Management/managementGroups/subscriptions@2023-04-01' = {
  parent: mg
  name: '<subscription guid>'
}
```

| Decision | Property |
|---|---|
| `group_id` | `name` |
| `display_name` | `properties.displayName` |
| `parent` | `properties.details.parent.id` (a tenant resource id) |
| `subscriptions` | one `managementGroups/subscriptions` child per guid |
| `role_assignments` | `Microsoft.Authorization/roleAssignments@2022-04-01` in a module with `scope: mg` |
