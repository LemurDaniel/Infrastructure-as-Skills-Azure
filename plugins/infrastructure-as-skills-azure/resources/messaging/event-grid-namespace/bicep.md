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

| Decision | Parameter | Note |
|---|---|---|
| `capacity` | **not carried by the module** - no `sku` parameter | The platform's one unit; a larger namespace is an authored `sku: { name: 'Standard', capacity }` |
| `minimum_tls_version` | **not carried by the module** | The API accepts `1.2` only; authored to write |
| `local_auth` | no parameter - the type has no switch | Recorded `forced`; no `listKeys`, no key output. Roles only |
| `zone_redundant` | `isZoneRedundant` | No module default (the platform decides when unset); written. Fixed at creation |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `namespace_topics`, `event_retention_days` | `topics: [ { name, eventRetentionInDays, inputSchema: 'CloudEventSchemaV1_0', eventSubscriptions } ]` | Untyped array; member names from the `topic` child README |
| `topic_subscriptions`, `delivery_mode` | `topics[].eventSubscriptions[]: { name, eventDeliverySchema, deliveryConfiguration: { deliveryMode: 'Queue' / 'Push', queue / push } }` | |
| `event_retention_days` (again) | `deliveryConfiguration.queue.eventTimeToLive` | ISO 8601, `'P7D'` |
| `max_delivery_count` | `deliveryConfiguration.queue.maxDeliveryCount` | Service default 10; written |
| `receive_lock_duration_seconds` | `deliveryConfiguration.queue.receiveLockDurationInSeconds` | |
| `keep_undeliverable_events`, `dead_letter_*` | `deliveryConfiguration.<mode>.deadLetterDestinationWithResourceIdentity: { identity, deadLetterDestination: { endpointType: 'StorageBlob', properties: { resourceId, blobContainerName } } }` | The identity form; no key |
| `mqtt_broker` | `topicSpacesState: 'Enabled'` / `'Disabled'` | Module default `'Disabled'`; written. Cannot be disabled again |
| `topic_spaces` | `topicSpaces: [ { name, topicTemplates } ]` | |
| `clients` | `clients: [ { name, authenticationName, attributes, clientCertificateAuthenticationValidationScheme, clientCertificateAuthenticationAllowedThumbprints } ]` | |
| `client_groups` | `clientGroups: [ { name, query } ]` | |
| `permission_bindings` | `permissionBindings: [ { name, clientGroupName, topicSpaceName, permission } ]` | By **name**, where the Terraform module takes map keys |
| `mqtt_routing`, `mqtt_routing_topic` | `routeTopicResourceId`, `routingIdentityInfo: { type: 'SystemAssigned' }` | Two-pass when the topic is created in the same run |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Module default `'Enabled'`; written |
| `ip_rules` | `inboundIpRules: [ { ipMask, action: 'Allow' } ]` | Used only with public access `Enabled` |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'topic' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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

| Decision | Property |
|---|---|
| `capacity` | `sku: { name: 'Standard', capacity }` (beside `properties`) |
| `minimum_tls_version` | `properties.minimumTlsVersionAllowed` |
| `zone_redundant` | `properties.isZoneRedundant` |
| `public_network_access`, `ip_rules` | `properties.publicNetworkAccess`, `properties.inboundIpRules` |
| `managed_identity` | `identity` (top level) |
| `mqtt_broker`, `mqtt_routing*` | `properties.topicSpacesConfiguration: { state, routeTopicResourceId, routingIdentityInfo }` |
| `namespace_topics`, `topic_subscriptions` | child `topics` with `properties: { eventRetentionInDays, inputSchema }` and `topics/eventSubscriptions` with `properties.deliveryConfiguration` |
| MQTT content | child `topicSpaces`, `clients`, `clientGroups`, `permissionBindings`, `caCertificates` |
