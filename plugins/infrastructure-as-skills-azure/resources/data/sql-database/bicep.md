# Rendering an Azure SQL Database server as Bicep

Mapping from the question set to the server and its databases. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/sql-database.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/sql/server:<version>` | **0.22.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `databases` | `databases: [ { name, ... } ]` | |
| `collation` | `databases[].collation` | Fixed at creation |
| `service_tier`, `compute_tier`, `vcores` | `databases[].sku: { name: 'GP_Gen5', tier: 'GeneralPurpose', family: 'Gen5', capacity: 2 }`; serverless `name: 'GP_S_Gen5'`; `'BusinessCritical'` / `'Hyperscale'` with `BC_Gen5` / `HS_Gen5` | Name, tier, family and capacity are four fields here, one string in Terraform |
| `min_vcores` | `databases[].minCapacity` | A **string** (`'0.5'`) |
| `auto_pause_delay_minutes` | `databases[].autoPauseDelay` | Serverless only |
| `max_size_gb` | `databases[].maxSizeBytes` | **Bytes** |
| `elastic_pool`, `pool_vcores` | `elasticPools: [ { name, sku: { name, tier, capacity }, perDatabaseSettings, zoneRedundant } ]` and `databases[].elasticPoolResourceId` | |
| `zone_redundant` | `databases[].zoneRedundant` (and the pool's) | Written; `availabilityZone` is a **required** property of a database (`-1`: no preference) |
| `geo_failover_region` | **not one call** - see below | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` | A string here, a bool in Terraform; default is empty (unset); written |
| `ip_rules` | `firewallRules: [ { name, startIpAddress, endIpAddress } ]` | |
| `allow_azure_services` | `firewallRules` entry `0.0.0.0` - `0.0.0.0` | |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'sqlServer' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `minimum_tls_version` | `minimalTlsVersion` | `'1.2'` or `'1.3'`; default `'1.2'`; written |
| `managed_identity` | `managedIdentities: { systemAssigned, userAssignedResourceIds }`, `primaryUserAssignedIdentityResourceId` | |
| `entra_admin`, `local_authentication_disabled` | `administrators: { administratorType: 'ActiveDirectory', azureADOnlyAuthentication: true, login, sid, principalType: 'Group', tenantId }` and **no** `administratorLogin`/`administratorLoginPassword` | |
| `database_users` | **not the module** | T-SQL after the deployment |
| `role_assignments` | `roleAssignments` | Control plane |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, autoRotationEnabled: true, userAssignedIdentityResourceId }` and `keys` | Unversioned |
| `threat_detection` | `securityAlertPolicies: [ { name: 'Default', state: 'Enabled' } ]` | |
| `vulnerability_assessment` | **not the module** for the express form (`vulnerabilityAssessmentsObj` is the classic one and wants a storage account) - `Microsoft.Sql/servers/sqlVulnerabilityAssessments` | |
| `short_term_retention_days` | `databases[].backupShortTermRetentionPolicy: { retentionDays, diffBackupIntervalInHours }` | |
| `long_term_retention` | `databases[].backupLongTermRetentionPolicy: { weeklyRetention }` | `'P13W'`, `'P52W'` |
| `backup_storage_redundancy` | `databases[].requestedBackupStorageRedundancy` | Written |
| `auditing_enabled` | `auditSettings: { state: 'Enabled', isAzureMonitorTargetEnabled: true }` **and** a diagnostic setting on `master` | Module default `{ state: 'Enabled' }` records to no destination at all; written |
| `diagnostic_workspace`, `diagnostic_categories`, `metrics_enabled` | `databases[].diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'Basic' } ] } ]` | Not `AllMetrics` for a database |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module sql 'br/public:avm/res/sql/server:0.22.1' = {
  name: 'sql-database'
  params: {
    name: sqlName
    location: location
    tags: tags

    // decision: sql-database.security.local_authentication_disabled / identity.entra_admin
    // Entra-only: no administratorLogin, no password
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: entraAdminLogin
      sid: entraAdminObjectId
      principalType: 'Group'
      tenantId: tenantId
    }
    minimalTlsVersion: '1.2'

    // decision: sql-database.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    firewallRules: []
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'sqlServer'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    managedIdentities: { systemAssigned: true }

    // decision: sql-database.security.threat_detection
    securityAlertPolicies: [ { name: 'Default', state: 'Enabled' } ]

    // decision: sql-database.observability.auditing_enabled - to Azure Monitor
    auditSettings: {
      state: 'Enabled'
      isAzureMonitorTargetEnabled: true
    }

    // decision: sql-database.database.databases
    databases: [
      {
        name: 'app'
        // decision: sql-database.database.service_tier / compute_tier / vcores
        sku: { name: 'GP_Gen5', tier: 'GeneralPurpose', family: 'Gen5', capacity: 2 }
        collation: 'SQL_Latin1_General_CP1_CI_AS'
        availabilityZone: -1 // required by the module; -1 is no preference
        maxSizeBytes: 34359738368 // 32 GB
        // decision: sql-database.resilience.zone_redundant
        zoneRedundant: true
        // decision: sql-database.data_protection.backup_storage_redundancy
        requestedBackupStorageRedundancy: 'Zone'
        // decision: sql-database.data_protection.short_term_retention_days
        backupShortTermRetentionPolicy: { retentionDays: 7, diffBackupIntervalInHours: 12 }
        // decision: sql-database.data_protection.long_term_retention
        backupLongTermRetentionPolicy: { weeklyRetention: 'P13W' }
        diagnosticSettings: [
          {
            workspaceResourceId: diagnosticWorkspaceId
            logCategoriesAndGroups: [
              { category: 'Errors' }
              { category: 'Timeouts' }
              { category: 'Blocks' }
              { category: 'Deadlocks' }
            ]
            metricCategories: [ { category: 'Basic' } ]
          }
        ]
      }
    ]

    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = sql.outputs.resourceId
output name string = sql.outputs.name
```

A serverless database replaces the sku and size by
`sku: { name: 'GP_S_Gen5', tier: 'GeneralPurpose', family: 'Gen5', capacity: 2 }`,
`minCapacity: '0.5'` and `autoPauseDelay: 60`; a pooled one takes `sku: { name: 'ElasticPool' }` and
`elasticPoolResourceId`.

### The audit diagnostic and the express assessment

The audit setting above sends nothing by itself: the destination is a diagnostic setting on the
`master` database. The express vulnerability assessment is a child of the server that the module
does not expose:

```bicep
resource server 'Microsoft.Sql/servers@2024-05-01-preview' existing = {
  name: sqlName
  dependsOn: [ sql ]
}

resource master 'Microsoft.Sql/servers/databases@2024-05-01-preview' existing = {
  parent: server
  name: 'master'
}

// decision: sql-database.observability.auditing_enabled
resource auditDiagnostic 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'audit'
  scope: master
  properties: {
    workspaceId: diagnosticWorkspaceId
    logs: [ { category: 'SQLSecurityAuditEvents', enabled: true } ]
  }
}

// decision: sql-database.security.vulnerability_assessment - the express configuration, no storage account
resource expressAssessment 'Microsoft.Sql/servers/sqlVulnerabilityAssessments@2024-05-01-preview' = {
  parent: server
  name: 'default'
  properties: { state: 'Enabled' }
}
```

The Defender for SQL plan is a subscription resource and the platform's; nothing here enables it.

### Database users

Entra users are created in each database, as the Entra administrator, with
`CREATE USER [name] FROM EXTERNAL PROVIDER` and `ALTER ROLE db_datareader ADD MEMBER [name]`. No ARM
resource does it; it is a step after the deployment, recorded in the spec as `database_users`.

### A second region

`geo_failover_region` is a second instance of this module in that region and a
`Microsoft.Sql/servers/failoverGroups` (the module's `failoverGroups` parameter) on the primary
naming the partner server. The exact shape is read from the README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the
databases' tiers, retention and the audit settings. The `master` diagnostic and the express
assessment are top-level resources of the compiled template. `database_users` and the Defender plan
are `not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.Sql/servers`:

| Decision | Property |
|---|---|
| the server | `Microsoft.Sql/servers` (`version: '12.0'`) |
| `minimum_tls_version` | `properties.minimalTlsVersion` |
| `public_network_access` | `properties.publicNetworkAccess`, child `firewallRules` |
| `local_authentication_disabled`, `entra_admin` | `properties.administrators { administratorType, azureADOnlyAuthentication, login, sid, tenantId }`, no `administratorLogin` |
| `managed_identity` | `identity { type, userAssignedIdentities }`, `properties.primaryUserAssignedIdentityId` |
| `key_management` | `properties.keyId` and child `encryptionProtector` |
| `databases` | child `databases` (`sku`, `collation`, `maxSizeBytes`, `zoneRedundant`, `requestedBackupStorageRedundancy`, `minCapacity`, `autoPauseDelay`) |
| `short_term_retention_days`, `long_term_retention` | child `backupShortTermRetentionPolicies/default`, `backupLongTermRetentionPolicies/default` |
| `elastic_pool` | child `elasticPools` and `properties.elasticPoolId` |
| `auditing_enabled` | child `auditingSettings/default` and a diagnostic setting on `master` |
| `threat_detection` | child `securityAlertPolicies/Default` |
| `vulnerability_assessment` | child `sqlVulnerabilityAssessments/default` |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: ['sqlServer']` |
