# Rendering a Container Registry as Bicep

Mapping from the question set to the registry. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/container-registry.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/container-registry/registry:<version>` | **0.13.1** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide parameters, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'container-registry'
  params: {
    name: registryName
    location: location
    tags: tags

    acrSku: 'Premium'
    // decision: container-registry.registry.zone_redundant - fixed at creation
    zoneRedundancy: 'Enabled'
    replications: []
    // decision: container-registry.registry.retention_untagged_days - Terraform's default is 7
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 7

    // decision: container-registry.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: container-registry.networking.network_rule_bypass - the module default is AzureServices
    networkRuleBypassOptions: 'None'
    exportPolicyStatus: 'disabled'
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'registry'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: container-registry.security.admin_enabled
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ContainerRegistryRepositoryEvents' }
          { category: 'ContainerRegistryLoginEvents' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = registry.outputs.resourceId
output loginServer string = registry.outputs.loginServer
```

Output names are read from the README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.ContainerRegistry/registries` with `sku` and `properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
