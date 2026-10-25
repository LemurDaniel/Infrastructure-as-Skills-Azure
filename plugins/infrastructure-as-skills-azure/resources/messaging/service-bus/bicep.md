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

| Decision | Parameter | Note |
|---|---|---|
| `sku`, `capacity` | `skuObject: { name, capacity }` | Module default `Premium`, capacity 1; written. Standard and Basic take no capacity |
| `zone_redundant` | `zoneRedundant` | Module default **`true`**, which requires Premium; written, `false` below Premium |
| `premium_messaging_partitions` | `premiumMessagingPartitions` | Default 1; written |
| `minimum_tls_version` | `minimumTlsVersion` | Default `'1.2'`; written |
| `local_auth` | `disableLocalAuth` | **Inverse**: `disabled` is `true`; module default `true`. Terraform's default is the opposite |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Unset, it is disabled only when private endpoints are set |
| `public_network_access`, `ip_rules`, `trusted_service_bypass` | `networkRuleSets: { publicNetworkAccess, defaultAction, trustedServiceAccessEnabled, ipRules: [ { ipMask, action: 'Allow' } ] }` | Module default for trusted services is **`true`**; written. Premium only |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'namespace' } ]` | Premium only |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | Version unset: the latest, followed on rotation. Premium |
| `infrastructure_encryption` | `requireInfrastructureEncryption` | Module default **`true`** and then requires the key; written |
| `queues` | `queues: [ { name, ... } ]` | The namespace-wide settings below on each |
| `topics` | `topics: [ { name, subscriptions: [ { name, ... } ] } ]` | Standard or Premium |
| `message_ordering` | `queues[].requiresSession`, `topics[].subscriptions[].requiresSession` | Fixed at creation |
| `duplicate_protection` | `queues[].requiresDuplicateDetection`, `topics[].requiresDuplicateDetection` | Fixed at creation |
| `message_retention_days` | `defaultMessageTimeToLive` | ISO 8601: `'P14D'`; queue, topic and subscription |
| `dead_letter_on_expiry` | `deadLetteringOnMessageExpiration` | Queue and subscription |
| `max_delivery_count` | `maxDeliveryCount` | Queue and subscription |
| `lock_duration_seconds` | `lockDuration` | Queue and subscription; `'PT1M'` for 60 |
| `max_size_megabytes` | `maxSizeInMegabytes` | Queue and topic |
| `geo_recovery`, `partner_namespace` | `disasterRecoveryConfig: { partnerNamespace, alternateName }` | On the **primary** only; the partner is a second module call with no entities |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | Also per queue and topic |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). Entities are
checked in `parameters.queues.value[*]`.

## Authored rendering

The fallback. `Microsoft.ServiceBus/namespaces` with `properties`:

| Decision | Property |
|---|---|
| `sku`, `capacity` | `sku: { name, tier, capacity }` (top level, beside `properties`) |
| `zone_redundant` | `properties.zoneRedundant` |
| `premium_messaging_partitions` | `properties.premiumMessagingPartitions` |
| `minimum_tls_version` | `properties.minimumTlsVersion` |
| `local_auth` | `properties.disableLocalAuth` |
| `public_network_access` | `properties.publicNetworkAccess` (`'Disabled'`, `'Enabled'`) |
| `key_management` | `properties.encryption: { keySource: 'Microsoft.KeyVault', keyVaultProperties: [ { keyName, keyVaultUri, identity } ], requireInfrastructureEncryption }` |
| `network_rule_config` | child `networkRuleSets/default`: `defaultAction`, `ipRules`, `virtualNetworkRules`, `trustedServiceAccessEnabled`, `publicNetworkAccess` |
| `queues` | child `queues` with `properties` of the same names as the module's |
| `topics` | child `topics` and `topics/subscriptions` |
| `geo_recovery` | child `disasterRecoveryConfigs` on the primary |
