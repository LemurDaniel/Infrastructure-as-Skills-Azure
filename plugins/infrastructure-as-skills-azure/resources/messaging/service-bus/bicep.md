# Rendering a Service Bus namespace as Bicep

Mapping from the question set to the namespace. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/service-bus.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/service-bus/namespace:<version>` | **0.17.1** | 2026-10-25 |

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
module serviceBus 'br/public:avm/res/service-bus/namespace:0.17.1' = {
  name: 'service-bus'
  params: {
    name: serviceBusName
    location: location
    tags: tags

    // decision: service-bus.namespace.sku
    skuObject: {
      name: 'Premium'
      capacity: 1
    }
    zoneRedundant: true
    premiumMessagingPartitions: 1
    minimumTlsVersion: '1.2'
    // decision: service-bus.namespace.local_auth - inverse input
    disableLocalAuth: true
    // decision: service-bus.encryption.infrastructure_encryption - module default true
    requireInfrastructureEncryption: false

    // decision: service-bus.networking.public_network_access
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

    queues: [for q in queueNames: {
      name: q
      // decision: service-bus.entities.* - written on every queue
      requiresSession: false
      requiresDuplicateDetection: false
      defaultMessageTimeToLive: 'P14D'
      deadLetteringOnMessageExpiration: true
      maxDeliveryCount: 10
      lockDuration: 'PT1M'
      maxSizeInMegabytes: 1024
    }]

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'OperationalLogs' }
          { category: 'VNetAndIPFilteringLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = serviceBus.outputs.resourceId
```

`networkRuleSets.publicNetworkAccess` repeats the top-level parameter on purpose: with `Disabled`
the module does not apply network rules, with `Enabled` it applies `defaultAction`, and a render
that sets only one leaves the other at the module's default.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). Entities are
checked in `parameters.queues.value[*]`.

## Authored rendering

The fallback. `Microsoft.ServiceBus/namespaces` with `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
