# Rendering an Event Grid system topic as Bicep

Mapping from the question set to the topic. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/event-grid-system-topic.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/event-grid/system-topic:<version>` | **0.7.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The
module deploys the topic with API version `2025-02-15`; `eventSubscriptions` is an untyped
array whose members follow the ARM `systemTopics/eventSubscriptions` shape.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `location` | `location` | Module default `resourceGroup().location`; **written**: the source's region, `'global'` for `Microsoft.Resources.*` topic types |
| `source_resource` | `source` | Required by the module; fixed at creation |
| `topic_type` | `topicType` | Required by the module; exact casing; fixed at creation |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `event_subscriptions` | `eventSubscriptions: [ { name, deliveryWithResourceIdentity, filter, retryPolicy, deadLetterWithResourceIdentity, eventDeliverySchema } ]` | One member per entry |
| `destination_kind` | `deliveryWithResourceIdentity.destination.endpointType`: `'ServiceBusQueue'`, `'ServiceBusTopic'`, `'StorageQueue'`, `'EventHub'`, `'AzureFunction'`, `'WebHook'`, `'HybridConnection'`, with `properties.resourceId` (`endpointUrl` for a webhook, `queueName` added for a storage queue) | |
| `managed_identity` (delivery) | `deliveryWithResourceIdentity.identity: { type: 'SystemAssigned' }` and `deadLetterWithResourceIdentity.identity` | Under `none`, the key-based `destination` and `deadLetterDestination` members instead |
| `event_delivery_schema` | `eventSubscriptions[].eventDeliverySchema` | Platform default `EventGridSchema`; written |
| `included_event_types` | `eventSubscriptions[].filter.includedEventTypes` | Empty delivers every type |
| subject filter (content of the entry) | `filter.subjectBeginsWith`, `subjectEndsWith` | |
| `max_delivery_attempts`, `event_ttl_minutes` | `retryPolicy: { maxDeliveryAttempts, eventTimeToLiveInMinutes }` | |
| `keep_undeliverable_events`, `dead_letter_*` | `deadLetterWithResourceIdentity: { identity, deadLetterDestination: { endpointType: 'StorageBlob', properties: { resourceId, blobContainerName } } }` | |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| roles on the targets | `externalResourceRoleAssignments` exists; **not used** - wiring belongs to the pattern | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.resource_lock` | no `lock` - the type is not on the list | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module systemTopic 'br/public:avm/res/event-grid/system-topic:0.7.0' = {
  name: 'event-grid-system-topic'
  params: {
    name: systemTopicName
    // decision: event-grid-system-topic.placement.location - the source's region, global for Microsoft.Resources.*
    location: location
    tags: tags

    // decision: event-grid-system-topic.source.source_resource, topic_type - both fixed at creation
    source: sourceResourceId
    topicType: 'Microsoft.Storage.StorageAccounts'

    // decision: event-grid-system-topic.source.managed_identity
    managedIdentities: { systemAssigned: true }

    eventSubscriptions: [
      {
        name: 'uploads-worker'
        // decision: event-grid-system-topic.delivery.event_delivery_schema
        eventDeliverySchema: 'CloudEventSchemaV1_0'
        // decision: event-grid-system-topic.destination_kind, managed_identity - delivery with the topic's identity, no key
        deliveryWithResourceIdentity: {
          identity: { type: 'SystemAssigned' }
          destination: {
            endpointType: 'ServiceBusQueue'
            properties: { resourceId: uploadsQueueId }
          }
        }
        // decision: event-grid-system-topic.delivery.included_event_types - empty delivers every type
        filter: {
          includedEventTypes: [ 'Microsoft.Storage.BlobCreated' ]
          subjectBeginsWith: '/blobServices/default/containers/uploads/'
        }
        // decision: event-grid-system-topic.delivery.max_delivery_attempts, event_ttl_minutes
        retryPolicy: {
          maxDeliveryAttempts: 30
          eventTimeToLiveInMinutes: 1440
        }
        // decision: event-grid-system-topic.delivery.keep_undeliverable_events, dead_letter_*
        deadLetterWithResourceIdentity: {
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
    ]

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [ { category: 'DeliveryFailures' } ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = systemTopic.outputs.resourceId
output principalId string = systemTopic.outputs.?systemAssignedMIPrincipalId ?? ''
```

The subscriptions array is built from the spec's `event_subscriptions`, one member per entry
with the entry's `endpointType` and target id. The identity's role on each target and on the
dead-letter container is wiring, granted by the pattern before this module runs - in a
separate deployment when the topic's system-assigned identity is created here, because its
principal id is unknown until then (the usual reason a pattern picks `user_assigned`). A
webhook destination is an `open:` entry.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `source`,
`topicType`, `location`, `managedIdentities.systemAssigned`, and the `eventSubscriptions`
array down to `retryPolicy.maxDeliveryAttempts` and `deadLetterWithResourceIdentity`.

## Authored rendering

The fallback. `Microsoft.EventGrid/systemTopics@2025-02-15` with `identity` and `properties`:

| Decision | Property |
|---|---|
| `location` | `location` (the source's, or `'global'`) |
| `source_resource`, `topic_type` | `properties.source`, `properties.topicType` |
| `managed_identity` | `identity` (top level) |
| `event_subscriptions` and the delivery decisions | child `Microsoft.EventGrid/systemTopics/eventSubscriptions@2025-02-15` with `properties: { deliveryWithResourceIdentity, filter, retryPolicy, deadLetterWithResourceIdentity, eventDeliverySchema }` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` scoped to the topic, `logs: [ { category: 'DeliveryFailures', enabled: true } ]`, `metrics: [ { category: 'AllMetrics', enabled: true } ]` |
