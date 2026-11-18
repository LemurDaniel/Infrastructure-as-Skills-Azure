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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
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
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the database's
policies, persistence and access-policy assignments.

## Authored rendering

The fallback. `Microsoft.Cache/redisEnterprise` with a child `databases` named `default`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

## Azure Cache for Redis (Basic, Standard, Premium)

Not covered by the question set, and on a retirement path (see [notes.md](notes.md)). A repository that already
renders it keeps the module `br/public:avm/res/cache/redis:<version>` (**0.18.0**), whose parameters differ:
`skuName` (`'Basic'`, `'Standard'`, `'Premium'`) with `capacity`, `redisConfiguration` (persistence,
`maxmemory-policy`, `aad-enabled`), `disableAccessKeyAuthentication`, `enableNonSslPort`, `availabilityZones`,
`subnetResourceId` for the injected Premium network, and `firewallRules`. Its private-endpoint sub-resource
is `redisCache`.
