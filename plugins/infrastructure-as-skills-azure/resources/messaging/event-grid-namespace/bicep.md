# Rendering an Event Grid namespace as Bicep

Mapping from the question set to the namespace. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/event-grid-namespace.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/event-grid/namespace:<version>` | **0.8.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The
module deploys the namespace with API version `2023-12-15-preview`.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | In the stages the deployment names |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module eventGridNamespace 'br/public:avm/res/event-grid/namespace:0.8.0' = {
  name: 'event-grid-namespace'
  params: {
    name: eventGridNamespaceName
    location: location
    tags: tags

    // decision: event-grid-namespace.namespace.zone_redundant - derived from outage_impact
    isZoneRedundant: true
    // decision: event-grid-namespace.namespace.managed_identity
    managedIdentities: { systemAssigned: true }

    // decision: event-grid-namespace.networking.public_network_access - module default Enabled
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

    // decision: event-grid-namespace.topics.namespace_topics, event_retention_days
    topics: [
      {
        name: 'orders'
        eventRetentionInDays: 7
        inputSchema: 'CloudEventSchemaV1_0'
        eventSubscriptions: [
          {
            name: 'orders-worker'
            eventDeliverySchema: 'CloudEventSchemaV1_0'
            deliveryConfiguration: {
              // decision: event-grid-namespace.topics.delivery_mode
              deliveryMode: 'Queue'
              queue: {
                // decision: event-grid-namespace.topics.event_retention_days - the TTL follows the topic
                eventTimeToLive: 'P7D'
                // decision: event-grid-namespace.topics.max_delivery_count
                maxDeliveryCount: 10
                // decision: event-grid-namespace.topics.receive_lock_duration_seconds
                receiveLockDurationInSeconds: 60
                // decision: event-grid-namespace.topics.keep_undeliverable_events
                deadLetterDestinationWithResourceIdentity: {
                  identity: { type: 'SystemAssigned' }
                  deadLetterDestination: {
                    endpointType: 'StorageBlob'
                    properties: {
                      resourceId: deadLetterStorageAccountId
                      blobContainerName: 'eventgrid-deadletter'
                    }
                  }
                }
              }
            }
          }
        ]
      }
    ]

    // decision: event-grid-namespace.mqtt.mqtt_broker - cannot be disabled again once Enabled
    topicSpacesState: 'Disabled'
    topicSpaces: topicSpaces
    clients: clients
    clientGroups: clientGroups
    permissionBindings: permissionBindings

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'FailedHttpDataPlaneOperations' }
          { category: 'FailedMqttConnections' }
          { category: 'FailedMqttPublishedMessages' }
          { category: 'MqttDisconnections' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = eventGridNamespace.outputs.resourceId
```

With `mqtt_broker: true` the call writes `topicSpacesState: 'Enabled'`, fills the four MQTT
arrays from the spec and, under `mqtt_routing: event_grid_topic`, adds `routeTopicResourceId`
and `routingIdentityInfo: { type: 'SystemAssigned' }` in a second deployment once the topic
and the identity's role on it exist.

`capacity` above one and `minimum_tls_version` are not carried by the module: the render
either accepts the platform's values and records them `forced` with the module as `forced_by`,
or renders the namespace authored (below) and keeps the module for nothing. A push
subscription takes `deliveryConfiguration.push.deliveryWithResourceIdentity` with the
namespace's identity; its role on the target is wiring, ordered by the pattern. A webhook
destination is an `open:` entry.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision the module carries is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `isZoneRedundant`,
`publicNetworkAccess`, `topicSpacesState`, the `topics` array down to
`deliveryConfiguration.queue.maxDeliveryCount`. `capacity` and `minimum_tls_version` are
`# not-testable:` against the module call (no parameter) and asserted on the authored resource
where that path is taken.

## Authored rendering

The fallback, and the path for `capacity` above one or an explicit TLS floor.
`Microsoft.EventGrid/namespaces@2025-02-15` with `sku` and `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Properties no decision covers

| Input | Property |
|---|---|
| MQTT content without a decision | child `caCertificates` |
