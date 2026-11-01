# Rendering a Cosmos DB account as Bicep

Mapping from the question set to the account. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/cosmos-db.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/document-db/database-account:<version>` | **0.21.1** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

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
module cosmos 'br/public:avm/res/document-db/database-account:0.21.1' = {
  name: 'cosmos-db'
  params: {
    name: cosmosName
    location: location
    tags: tags

    capacityMode: 'Provisioned'
    enableFreeTier: false
    totalThroughputLimit: -1

    // decision: cosmos-db.resilience.zone_redundant
    failoverLocations: [
      { locationName: location, failoverPriority: 0, isZoneRedundant: true }
    ]
    enableAutomaticFailover: true
    // decision: cosmos-db.resilience.consistency_level - differs from the Terraform default
    defaultConsistencyLevel: 'Session'

    // decision: cosmos-db.networking.public_network_access
    networkRestrictions: {
      publicNetworkAccess: 'Disabled'
      networkAclBypass: 'None'
      ipRules: []
    }
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'Sql'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    disableLocalAuthentication: true
    disableKeyBasedMetadataWriteAccess: true

    // decision: cosmos-db.data_protection.backup_policy
    backupPolicyType: 'Continuous'
    backupPolicyContinuousTier: 'Continuous7Days'
    enableAnalyticalStorage: false

    sqlDatabases: [
      {
        name: 'app'
        containers: [
          {
            name: 'conversations'
            paths: [ '/userId' ]
            autoscaleSettingsMaxThroughput: 1000
          }
        ]
      }
    ]

    sqlRoleAssignments: sqlRoleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ControlPlaneRequests' }
          { category: 'DataPlaneRequests' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = cosmos.outputs.resourceId
output endpoint string = cosmos.outputs.endpoint
```

The built-in data roles are `<account id>/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001`
(reader) and `...0002` (contributor); the exact shape of `sqlRoleAssignments` is read from the
README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the
containers and the data-plane roles, which the Terraform side cannot see through the module.

## Authored rendering

The fallback. `Microsoft.DocumentDB/databaseAccounts` with `kind: 'GlobalDocumentDB'`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
