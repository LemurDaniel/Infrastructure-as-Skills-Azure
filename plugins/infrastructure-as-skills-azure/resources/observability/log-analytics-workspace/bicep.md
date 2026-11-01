# Rendering a Log Analytics workspace as Bicep

Mapping from the question set to `Microsoft.OperationalInsights/workspaces`. General
layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/observability.bicep
```

## With the AVM module

`br/public:avm/res/operational-insights/workspace:<version>` — the primary rendering for
`observability_ownership: create`. Documented against **0.16.1** (resolved 2026-10-17);
resolve the current version and re-read its README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. A referenced workspace stays
an `existing` reference as below.

### Decision → module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter | Note |
|---|---|---|
| `managed_identity` | `managedIdentities: { systemAssigned: true }` | |
| `key_management: customer_managed` | `features.enableDataExport` is unrelated; CMK is a linked dedicated cluster, outside this question set | |
| diagnostics of the workspace itself | `diagnosticSettings: [ { workspaceResourceId, … } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module workspace 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'observability'
  params: {
    name: workspaceName
    location: location
    tags: tags

    skuName: 'PerGB2018'
    // decision: log-analytics-workspace.cost.retention_days - the module default is 365
    dataRetention: 30
    // decision: log-analytics-workspace.cost.daily_quota_gb - a string here, -1 is no cap
    dailyQuotaGb: '-1'

    // Both, or logs arrive and nobody can read them. The module defaults are Enabled.
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'

    features: {
      // The workspace key is a non-expiring bearer credential.
      disableLocalAuth: true
      // false: RBAC on the workspace governs reads, rather than permissions
      // inherited from whichever resource emitted the row.
      enableLogAccessUsingOnlyResourcePermissions: false
    }

    enableTelemetry: true
  }
}

output id string = workspace.outputs.resourceId
output name string = workspace.outputs.name
```

## Authored rendering

The fallback — `implementation: authored`, a repository that already renders the
workspace this way, or reading what the module does inside.

## Decision → property

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Note the shape difference from Terraform: the two access switches are string enums
(`'Enabled'` / `'Disabled'`) rather than booleans, and the feature flags sit in a nested
`features` object instead of being top-level arguments.

## The workspace

```bicep
// locationCodes, environmentCodes and the index param as in naming.md, generated from naming.yaml.
// patterns.Azure.default, abbreviation `log`:
// <TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<INDEX>  ->  log-we-dev-platform-01
var workspaceName = 'log-${locationCodes[location]}-${environmentCodes[environment]}-${workload}-${padLeft(index, 2, '0')}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags

  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30

    workspaceCapping: {
      dailyQuotaGb: -1
    }

    // Both, or logs arrive and nobody can read them.
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'

    features: {
      // The workspace key is a non-expiring bearer credential.
      disableLocalAuth: true
      // false: RBAC on the workspace governs reads, rather than permissions
      // inherited from whichever resource emitted the row.
      enableLogAccessUsingOnlyResourcePermissions: false
    }
  }
}

output id string = workspace.id
output name string = workspace.name
```

## Referencing one instead

`observability_ownership: reference` renders an `existing` reference, and the workspace
usually lives in a platform resource group — so the `scope:` is not optional:

```bicep
resource platformWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: workspaceName
  scope: resourceGroup(workspaceResourceGroupName)
}
```

Pass `platformWorkspace.id` down to the modules that diagnose into it, rather than
repeating the `existing` block in each one — the lookup is free, but five copies of a name
parameter is five places to change.

## Deletion

Soft delete is Azure's behaviour, not a template property: there is no field here to set.
A permanent delete is a `forceDelete=true` query parameter on the REST call, which
`az monitor log-analytics workspace delete --force` sends. A `what-if` will not show that
a name is still reserved from a previous delete — that surfaces only at deployment.
