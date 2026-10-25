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

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `skuName` | Module default `'Standard'`; written |
| `capacity` | `skuCapacity` | Default 1; written |
| `auto_inflate`, `maximum_throughput_units` | `isAutoInflateEnabled`, `maximumThroughputUnits` | Module default off, ceiling 1; written |
| `minimum_tls_version` | `minimumTlsVersion` | Default `'1.2'`; written |
| `local_auth` | `disableLocalAuth` | **Inverse**: `disabled` is `true`; module default `true` |
| `zone_redundant` | `zoneRedundant` | Module default **`true`**; written |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Unset, disabled only when private endpoints are set |
| `public_network_access`, `ip_rules`, `trusted_service_bypass` | `networkRuleSets: { publicNetworkAccess, defaultAction, trustedServiceAccessEnabled, ipRules: [ { ipMask, action: 'Allow' } ] }` | |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'namespace' } ]` | Standard or above |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | |
| `infrastructure_encryption` | `requireInfrastructureEncryption` | Default `false`; written |
| `event_hubs`, `partition_count`, `message_retention_days` | `eventhubs: [ { name, partitionCount, messageRetentionInDays } ]` | `messageRetentionInDays` 1-7 below Premium |
| `consumer_groups` | `eventhubs[].consumergroups: [ { name } ]` | |
| `event_archive`, `archive_*` | `eventhubs[].captureDescription: { enabled, encoding: 'Avro', intervalInSeconds, destination: { name, properties: { storageAccountResourceId, blobContainerName, archiveNameFormat } } }` | Read the member names from the README |
| `geo_recovery`, `partner_namespace` | `disasterRecoveryConfig: { partnerNamespace, alternateName }` | On the primary only |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | Also per event hub |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). Event hubs are
checked in `parameters.eventhubs.value[*]`.

## Authored rendering

The fallback. `Microsoft.EventHub/namespaces` with `sku: { name, tier, capacity }` and
`properties`:

| Decision | Property |
|---|---|
| `auto_inflate` | `properties.isAutoInflateEnabled`, `maximumThroughputUnits` |
| `minimum_tls_version` | `properties.minimumTlsVersion` |
| `local_auth` | `properties.disableLocalAuth` |
| `zone_redundant` | `properties.zoneRedundant` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `key_management` | `properties.encryption: { keySource: 'Microsoft.KeyVault', keyVaultProperties, requireInfrastructureEncryption }` |
| `network_rulesets` | child `networkRuleSets/default` |
| `event_hubs` | child `eventhubs` with `properties: { partitionCount, messageRetentionInDays, captureDescription }` |
| `consumer_groups` | child `eventhubs/consumergroups` |
| `geo_recovery` | child `disasterRecoveryConfigs` on the primary |
