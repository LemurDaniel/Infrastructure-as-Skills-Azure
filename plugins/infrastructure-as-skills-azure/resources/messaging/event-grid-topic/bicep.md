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

| Decision | Parameter | Note |
|---|---|---|
| `input_schema` | `inputSchema` | Module default `'EventGridSchema'`; written. Fixed at creation |
| `minimum_tls_version` | `minimumTlsVersionAllowed` | Default `'1.2'`; written |
| `local_auth` | `disableLocalAuth` | Module default `true`; written |
| `data_residency_boundary` | `dataResidencyBoundary` | `'WithinRegion'` / `'WithinGeopair'` |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Module default `''` (left to the platform); written |
| `ip_rules` | `inboundIpRules: [ { ipMask, action: 'Allow' } ]` | Used only with public access `Enabled` |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'topic' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `event_subscriptions` | `eventSubscriptions: [ { name, destination, deliveryWithResourceIdentity, filter, retryPolicy, deadLetterWithResourceIdentity } ]` | Identity-based delivery, never a key; read the member names from the README |
| `max_delivery_attempts`, `event_ttl_minutes` | `eventSubscriptions[].retryPolicy: { maxDeliveryAttempts, eventTimeToLiveInMinutes }` | |
| `keep_undeliverable_events`, `dead_letter_*` | `eventSubscriptions[].deadLetterWithResourceIdentity` | |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.EventGrid/topics` with `properties`:

| Decision | Property |
|---|---|
| `input_schema` | `properties.inputSchema` |
| `minimum_tls_version` | `properties.minimumTlsVersionAllowed` |
| `local_auth` | `properties.disableLocalAuth` |
| `data_residency_boundary` | `properties.dataResidencyBoundary` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `ip_rules` | `properties.inboundIpRules` |
| `event_subscriptions` | child `eventSubscriptions` with `properties: { destination, filter, retryPolicy, deadLetterWithResourceIdentity }` |
