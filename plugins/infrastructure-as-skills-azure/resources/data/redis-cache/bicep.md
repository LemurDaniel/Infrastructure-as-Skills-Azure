# Rendering Azure Managed Redis as Bicep

Mapping from the question set to the cluster and its database. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/redis-cache.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/cache/redis-enterprise:<version>` | **0.5.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module builds the
cluster and, through its `database` parameter, the database `default`.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku_name` | `skuName: 'Balanced_B1'` | Module default **`'Balanced_B5'`**; written. `capacity` applies to the older `Enterprise_*` SKUs only |
| `clustering_policy` | `database.clusteringPolicy` | `'EnterpriseCluster'`, `'OSSCluster'`, `'NoCluster'` |
| `eviction_policy` | `database.evictionPolicy` | |
| `redis_modules` | `database.modules: [ { name, args } ]` | |
| `high_availability` | `highAvailability: 'Enabled'` / `'Disabled'` | Module default `'Enabled'`; written. `availabilityZones` (default `[1, 2, 3]`) is documented as supported on the Enterprise SKUs only and is left at its default |
| `geo_replicas` | `database.geoReplication: { groupNickname, linkedDatabases }` | One instance per region; shape read from the pinned README |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` | A string; **required**; written |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'redisEnterprise' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | User-assigned only |
| `data_access_assignments` | `database.accessPolicyAssignments: [ { userObjectId, accessPolicyName: 'default' } ]` | |
| `role_assignments` | `roleAssignments` | Control plane |
| `access_keys_authentication_disabled` | `database.accessKeysAuthentication: 'Disabled'` / `'Enabled'` | Written |
| `encrypted_connections_only` | `database.clientProtocol: 'Encrypted'`, `minimumTlsVersion: '1.2'` | `'1.2'` is the only allowed value; written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, userAssignedIdentityResourceId }` | Unversioned |
| `persistence` | `database.persistence: { type: 'rdb', frequency: '1h' }`, `{ type: 'aof', frequency: '1s' }` or `{ type: 'disabled' }` | Written |
| `diagnostic_workspace`, `diagnostic_categories` | `database.diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category: 'ConnectionEvents' } ] } ]` | Logs only on the database |
| `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, metricCategories: [ { category: 'AllMetrics' } ] } ]` | Metrics only on the cluster |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module redis 'br/public:avm/res/cache/redis-enterprise:0.5.1' = {
  name: 'redis-cache'
  params: {
    name: redisName
    location: location
    tags: tags

    // decision: redis-cache.cache.sku_name - the module default is Balanced_B5
    skuName: 'Balanced_B1'

    // decision: redis-cache.resilience.high_availability
    highAvailability: 'Enabled'

    // decision: redis-cache.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'redisEnterprise'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]

    database: {
      name: 'default'
      // decision: redis-cache.cache.clustering_policy / eviction_policy / redis_modules
      clusteringPolicy: 'EnterpriseCluster'
      evictionPolicy: 'AllKeysLRU'
      modules: []
      // decision: redis-cache.security.encrypted_connections_only
      clientProtocol: 'Encrypted'
      // decision: redis-cache.security.access_keys_authentication_disabled
      accessKeysAuthentication: 'Disabled'
      // decision: redis-cache.data_protection.persistence - disabled: a cache is rebuilt from its source
      persistence: { type: 'disabled' }
      // decision: redis-cache.identity.data_access_assignments - the database's one access policy
      accessPolicyAssignments: [
        { userObjectId: appIdentityPrincipalId, accessPolicyName: 'default' }
      ]
      diagnosticSettings: [
        {
          workspaceResourceId: diagnosticWorkspaceId
          logCategoriesAndGroups: [ { category: 'ConnectionEvents' } ]
        }
      ]
    }

    minimumTlsVersion: '1.2'
    enableTelemetry: true
  }
}

output id string = redis.outputs.resourceId
output hostName string = redis.outputs.hostName
```

A cache that is not highly available sets `highAvailability: 'Disabled'`. A
customer-managed key adds `customerManagedKey` and a user-assigned identity in `managedIdentities`.
Persistence on is `{ type: 'rdb', frequency: '1h' }` (`'1h'`, `'6h'`, `'12h'`) or
`{ type: 'aof', frequency: '1s' }`.

### Data access

With access keys off, a client signs in with a Microsoft Entra token; the object id in
`accessPolicyAssignments` is the identity that is allowed to. The client library must support Entra
authentication and refresh the token before it expires.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the database's
policies, persistence and access-policy assignments.

## Authored rendering

The fallback. `Microsoft.Cache/redisEnterprise` with a child `databases` named `default`:

| Decision | Property |
|---|---|
| `sku_name` | `sku.name` |
| `high_availability` | `properties.highAvailability` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `encrypted_connections_only` | `properties.minimumTlsVersion`; database `properties.clientProtocol` |
| `clustering_policy`, `eviction_policy`, `redis_modules` | database `properties.clusteringPolicy`, `evictionPolicy`, `modules` |
| `access_keys_authentication_disabled`, `persistence` | database `properties.accessKeysAuthentication`, `persistence` |
| `data_access_assignments` | database child `accessPolicyAssignments` |
| `key_management` | `properties.encryption.customerManagedKeyEncryption`, `identity` |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: ['redisEnterprise']` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` on the database (logs) and the cluster (metrics) |

## Azure Cache for Redis (Basic, Standard, Premium)

Not covered by the question set, and on a retirement path (see [notes.md](notes.md)). A repository that already
renders it keeps the module `br/public:avm/res/cache/redis:<version>` (**0.18.0**), whose parameters differ:
`skuName` (`'Basic'`, `'Standard'`, `'Premium'`) with `capacity`, `redisConfiguration` (persistence,
`maxmemory-policy`, `aad-enabled`), `disableAccessKeyAuthentication`, `enableNonSslPort`, `availabilityZones`,
`subnetResourceId` for the injected Premium network, and `firewallRules`. Its private-endpoint sub-resource
is `redisCache`.
