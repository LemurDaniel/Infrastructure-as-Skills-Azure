# Rendering Application Insights as Bicep

Mapping from the question set to the component. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/application-insights.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/insights/component:<version>` | **0.8.0** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter | Note |
|---|---|---|
| (retention) | `retentionInDays` | Module default **365**; set to the workspace's retention |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'application-insights'
  params: {
    name: insightsName
    location: location
    tags: tags
    workspaceResourceId: workspaceResourceId

    applicationType: 'web'
    // decision: application-insights.component.sampling_percentage
    samplingPercentage: 100
    // decision: application-insights.component.store_client_ip - the module default stores them
    disableIpMasking: false

    // decision: application-insights.networking.public_network_access - the module default is Enabled
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'

    // decision: application-insights.security.local_authentication_disabled
    disableLocalAuth: true

    retentionInDays: workspaceRetentionDays // follows the workspace
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = insights.outputs.resourceId
output connectionString string = insights.outputs.connectionString
```

Parameter and output spellings are read from the README of the pinned version. The scoped
resource that adds the component to the platform's Private Link Scope is declared in the
scope's resource group, outside this call - and, as the scope is the platform's, usually by the
platform; the spec records it as `private_link_scope` and an `open:` entry when nobody could
name it.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Insights/components` with `kind: 'web'` and `properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
