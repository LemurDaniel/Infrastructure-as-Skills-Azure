# Rendering a role assignment as Bicep

Mapping from the question set to a standalone assignment. General layout, parameters and naming are
in [../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
Which assignments come here and which go through a module's `roleAssignments` interface is
decided in [notes.md](notes.md#interface-or-standalone).

```bash
bicep build --stdout modules/role-assignments.bicep
```

## With the AVM modules

**There is no single module.** A role assignment's template scope is the scope it is written
at, so AVM publishes one module per scope kind, and the render picks by `scope_kind`. The
top-level `avm/res/authorization/role-assignment` is **not published** (its README says so; only
the three scope children are). The `avm/ptn/authorization/role-assignment` pattern deploys at
management group scope for every kind and is not used here: a workload pipeline writing a
resource-group assignment should not need a deployment at a management group.

| `scope_kind` | Module | Documented against | Resolved | Template scope of the caller |
|---|---|---|---|---|
| `resource_group` | `br/public:avm/res/authorization/role-assignment/rg-scope:<version>` | **0.1.1** | 2026-10-25 | Resource group |
| `subscription` | `br/public:avm/res/authorization/role-assignment/sub-scope:<version>` | **0.1.1** | 2026-10-25 | Subscription (`targetScope = 'subscription'`) |
| `management_group` | `br/public:avm/res/authorization/role-assignment/mg-scope:<version>` | **0.1.2** | 2026-10-25 | Management group |
| `resource` | `br/public:avm/ptn/authorization/resource-role-assignment:<version>` | **0.1.2** | 2026-10-25 | Resource group of the resource |

Resolve the current version of each and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `principal` | `principalId` | |
| `principal_type` | `principalType` | **`ServicePrincipal`** for a managed identity - the allowed list is `''`, `Device`, `ForeignGroup`, `Group`, `ServicePrincipal`, `User`, with no managed-identity value. Written always |
| `role` | `roleDefinitionIdOrName` (the three scope modules) / `roleDefinitionId` (the resource pattern) | The scope modules resolve a built-in **name** through their own table. The resource pattern needs the role definition id, `subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '<guid>')`, and takes `roleName` for logging. Ids are checked against the live definition, not recalled |
| `scope` | the call's `scope:` / the template's `targetScope`, or `resourceId` (resource pattern) | See the table above |
| `condition`, `condition_version` | `condition`, `conditionVersion` | The three scope modules only (`'2.0'` is their default). **The resource pattern has no condition parameter** - a conditioned assignment on a resource is rendered authored |
| `description` | `description` | |
| name | `name` | `guid(<scope id>, principalId, <role>)`. Optional on all four; pass it anyway so the name does not depend on a module's recipe |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `deployer_role` | *none* | Not in the template; the handover (see `notes.md`) |

### The calls

```bicep
// decision: role-assignment.placement.scope_kind: resource_group
module groupRole 'br/public:avm/res/authorization/role-assignment/rg-scope:0.1.1' = {
  name: 'ra-group'
  params: {
    name: guid(resourceGroup().id, principalId, roleName)
    roleDefinitionIdOrName: roleName
    principalId: principalId
    // decision: role-assignment.identity.principal_type
    principalType: 'ServicePrincipal'
    // decision: role-assignment.security.condition - empty is no condition
    condition: ''
    description: description
    enableTelemetry: true
  }
}

// decision: role-assignment.placement.scope_kind: resource
module resourceRole 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: 'ra-resource'
  params: {
    resourceId: scopeId
    name: guid(scopeId, principalId, roleDefinitionGuid)
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionGuid)
    roleName: roleName
    principalId: principalId
    principalType: 'ServicePrincipal'
    description: description
    enableTelemetry: true
  }
}
```

The `subscription` and `management_group` modules are called the same way from a template with
the matching `targetScope`; the management group module also takes `managementGroupId`. The
group, resource, subscription and management group calls were built with `bicep build` against
the versions in the table. Outputs are `name`, `resourceId` and `scope` (the group module adds
`resourceGroupName`); names are read from the README of the pinned version.

A module call is one assignment. The render loops over the spec's standalone entries with a
module array, and the caller of a given scope kind lives in a template whose `targetScope`
matches - a stage that mixes scope kinds has one small module file per kind, composed by the
root.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above except `deployer_role` is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback - a conditioned assignment on a resource, or a repository that renders assignments
this way. One `Microsoft.Authorization/roleAssignments@2022-04-01`:

```bicep
resource assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: target                      // an `existing` resource reference; omitted for the group
  name: guid(target.id, principalId, roleDefinitionGuid)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionGuid)
    principalId: principalId
    principalType: 'ServicePrincipal'
    condition: condition
    conditionVersion: empty(condition) ? null : '2.0'
    description: description
  }
}
```

The scope is set with `scope:` on an `existing` resource reference, so the resource must be
reachable in the template (the same group, or a module scope).
