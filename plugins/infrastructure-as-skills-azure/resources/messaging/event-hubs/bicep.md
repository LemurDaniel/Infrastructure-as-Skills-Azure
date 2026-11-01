# Rendering an Event Hubs namespace as Bicep

Mapping from the question set to the namespace. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/event-hubs.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/event-hub/namespace:<version>` | **0.15.2** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module eventHubs 'br/public:avm/res/event-hub/namespace:0.15.2' = {
  name: 'event-hubs'
  params: {
    name: eventHubsName
    location: location
    tags: tags

    // decision: event-hubs.namespace.sku
    skuName: 'Standard'
    skuCapacity: 1
    isAutoInflateEnabled: false
    minimumTlsVersion: '1.2'
    // decision: event-hubs.namespace.local_auth - inverse input
    disableLocalAuth: true
    zoneRedundant: true
    requireInfrastructureEncryption: false

    // decision: event-hubs.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    networkRuleSets: {
      publicNetworkAccess: 'Disabled'
    }
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'namespace'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    eventhubs: [for h in eventHubNames: {
      name: h
      // decision: event-hubs.entities.partition_count, message_retention_days
      partitionCount: 4
      messageRetentionInDays: 1
    }]

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'OperationalLogs' }
          { category: 'EventHubVNetConnectionEvent' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = eventHubs.outputs.resourceId
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). Event hubs are
checked in `parameters.eventhubs.value[*]`.

## Authored rendering

The fallback. `Microsoft.EventHub/namespaces` with `sku: { name, tier, capacity }` and
`properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
