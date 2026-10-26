# Rendering a subscription (vending) as Bicep

Mapping from the question set to the alias, its placement, providers and access. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/bicep-idiom.md).
Nothing here renders when `subscription_ownership` is `platform`.

```bash
bicep build --stdout main.subscription.bicep
```

The template's `targetScope` is `managementGroup`, deployed with `az deployment mg create
--management-group-id <group>` by the platform's pipeline identity.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `br/public:avm/ptn/lz/sub-vending:<version>` | **0.8.0** | 2026-10-26 | Available (pattern) |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/avm.md) says. Pin the exact version. The module
is instantiated once per subscription; a stack renders one call per stage from the stage file.

**Always write `resourceProviders`.** Left out, the module registers a long built-in list through a
deployment script that needs a resource group, a storage account, an identity and a virtual network
in the new subscription; `{}` registers none and deploys no script.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `subscription_ownership: deployment` | `subscriptionAliasEnabled: true` | `existingSubscriptionId` is the manage-only case, not this set's |
| `billing_scope` | `subscriptionBillingScope` | EA / MCA / MPA id, case sensitive |
| `workload_type` | `subscriptionWorkload` | `'Production'` / `'DevTest'`; module default `'Production'` - written |
| `alias_name` | `subscriptionAliasName` | Generated `sub-<workload>-<stage>` when empty |
| `display_name` | `subscriptionDisplayName` | The alias when empty |
| `context.tags` | `subscriptionTags` | Merged onto the subscription |
| `management_group` | `subscriptionManagementGroupId` + `subscriptionManagementGroupAssociationEnabled: true` | The id alone |
| `register_resource_providers` | `resourceProviders: { '<ns>': [] }` | **Module default is a long list**; `{}` for none |
| `location` | `deploymentScriptLocation` | Only read when providers are registered |
| `role_assignments` | `roleAssignmentEnabled: true` + `roleAssignments: [ { principalId, definition, relativeScope: '' } ]` | `definition` one of the five names or a definition id |
| `cancel_on_removal` | *recorded only* | A template never cancels a subscription |
| boundaries | `virtualNetworkEnabled: false` | The budget, identity and NSG parameters are omitted (nothing deploys without them) |
| `deployment.module_telemetry` | `enableTelemetry` | |

### The call

```bicep
targetScope = 'managementGroup'

param location string
param billingScope string
param managementGroupId string
param teamOwnersGroupId string
param tags object
param enableTelemetry bool = false

module subscription 'br/public:avm/ptn/lz/sub-vending:0.8.0' = {
  name: 'sub-payments-prod'
  params: {
    // decision: subscription.placement.subscription_ownership - deployment
    subscriptionAliasEnabled: true
    // decision: subscription.billing.billing_scope
    subscriptionBillingScope: billingScope
    // decision: subscription.billing.workload_type - DevTest outside production
    subscriptionWorkload: 'Production'
    // decision: subscription.billing.alias_name / display_name
    subscriptionAliasName: 'sub-payments-prod'
    subscriptionDisplayName: 'sub-payments-prod'
    subscriptionTags: tags
    // decision: subscription.placement.management_group
    subscriptionManagementGroupAssociationEnabled: true
    subscriptionManagementGroupId: managementGroupId
    // decision: subscription.service.register_resource_providers - the module default is a long list
    resourceProviders: {
      'Microsoft.Storage': []
      'Microsoft.Web': []
    }
    deploymentScriptLocation: location
    // decision: subscription.identity.role_assignments
    roleAssignmentEnabled: true
    roleAssignments: [
      {
        principalId: teamOwnersGroupId
        definition: 'Owner'
        relativeScope: ''
      }
    ]
    // not rendered here: the network comes from its own set
    virtualNetworkEnabled: false
    enableTelemetry: enableTelemetry
  }
}

output subscriptionId string = subscription.outputs.subscriptionId
```

The call was built with `bicep build` against the version in the table. Outputs include
`subscriptionId`, `subscriptionResourceId` and `subscriptionAcceptOwnershipState`; the first is
what the workload's stage file receives.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every parameter above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/bicep-idiom.md#tests)): the billing
scope, the workload, the alias and display name, the management group, `resourceProviders`, the
role assignments and `virtualNetworkEnabled`. `cancel_on_removal` and `subscription_ownership` are
`not-testable` as records in the spec.

## Authored rendering

The fallback: the alias is a tenant resource created from a management group deployment with
`scope: tenant()`; the placement is part of the alias's `additionalProperties`.

```bicep
targetScope = 'managementGroup'

param billingScope string
param tags object

resource alias 'Microsoft.Subscription/aliases@2021-10-01' = {
  scope: tenant()
  name: 'sub-payments-prod'
  properties: {
    displayName: 'sub-payments-prod'
    billingScope: billingScope
    workload: 'Production'
    additionalProperties: {
      managementGroupId: managementGroup().id
      tags: tags
    }
  }
}

output subscriptionId string = alias.properties.subscriptionId
```

| Decision | Property |
|---|---|
| `alias_name` | `name` |
| `display_name` | `properties.displayName` |
| `billing_scope` | `properties.billingScope` |
| `workload_type` | `properties.workload` |
| `management_group` | `properties.additionalProperties.managementGroupId` (the resource id of the group) |
| `context.tags` | `properties.additionalProperties.tags` |
| `role_assignments` | `Microsoft.Authorization/roleAssignments` in a module with `scope: subscription(alias.properties.subscriptionId)` |
| `register_resource_providers` | a deployment script, as the pattern does; or left to first use |
