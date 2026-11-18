# Rendering an Event Grid custom topic as Bicep

Mapping from the question set to the topic. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/event-grid-topic.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/event-grid/topic:<version>` | **0.10.0** | 2026-10-25 |

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
module eventGridTopic 'br/public:avm/res/event-grid/topic:0.10.0' = {
  name: 'event-grid-topic'
  params: {
    name: eventGridTopicName
    location: location
    tags: tags

    // decision: event-grid-topic.topic.input_schema - module default EventGridSchema
    inputSchema: 'CloudEventSchemaV1_0'
    minimumTlsVersionAllowed: '1.2'
    // decision: event-grid-topic.topic.local_auth
    disableLocalAuth: true
    dataResidencyBoundary: 'WithinGeopair'

    // decision: event-grid-topic.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    inboundIpRules: []
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'topic'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    eventSubscriptions: eventSubscriptions

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'DeliveryFailures' }
          { category: 'PublishFailures' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = eventGridTopic.outputs.resourceId
```

A delivery destination and its role are wiring, ordered by the pattern: the identity holds the
data-plane role on the target before the subscription exists. A webhook destination is an
`open:` entry.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.EventGrid/topics` with `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
