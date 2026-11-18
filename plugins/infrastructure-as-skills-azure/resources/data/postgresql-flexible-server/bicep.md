# Rendering a PostgreSQL Flexible Server as Bicep

Mapping from the question set to the server. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/postgresql-flexible-server.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/db-for-postgre-sql/flexible-server:<version>` | **0.16.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs and inputs no decision covers

| Input | Parameter | Note |
|---|---|---|
| `availability_zone` (not a question of the set) | `availabilityZone: -1` | **Required** by the module; `-1` is no preference |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module postgresql 'br/public:avm/res/db-for-postgre-sql/flexible-server:0.16.1' = {
  name: 'postgresql-flexible-server'
  params: {
    name: postgresqlName
    location: location
    tags: tags

    // decision: postgresql-flexible-server.server.postgres_version / compute_tier / sku_name - the module default version is 18
    version: '17'
    tier: 'GeneralPurpose'
    skuName: 'Standard_D2ds_v5'
    // decision: postgresql-flexible-server.server.storage_size_gb / storage_auto_grow
    storageSizeGB: 128
    autoGrow: 'Enabled'
    availabilityZone: -1

    // decision: postgresql-flexible-server.security.password_authentication_disabled
    // Entra-only: no administratorLogin, no password
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenantId
    }
    // decision: postgresql-flexible-server.identity.entra_admins
    administrators: [
      {
        objectId: entraAdminObjectId
        principalName: entraAdminName
        principalType: 'Group'
        tenantId: tenantId
      }
    ]

    // decision: postgresql-flexible-server.resilience.high_availability
    highAvailability: 'ZoneRedundant'
    // decision: postgresql-flexible-server.resilience.maintenance_window - differs from the Terraform default
    maintenanceWindow: {
      customWindow: 'Enabled'
      dayOfWeek: 0
      startHour: 2
      startMinute: 0
    }

    // decision: postgresql-flexible-server.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    firewallRules: []
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'postgresqlServer'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: postgresql-flexible-server.security.minimum_tls_version
    configurations: [
      { name: 'ssl_min_protocol_version', source: 'user-override', value: 'TLSv1.2' }
      { name: 'require_secure_transport', source: 'user-override', value: 'on' }
    ]
    // decision: postgresql-flexible-server.security.threat_protection
    enableAdvancedThreatProtection: true

    // decision: postgresql-flexible-server.data_protection.backup_retention_days
    backupRetentionDays: 7
    // decision: postgresql-flexible-server.data_protection.geo_redundant_backup - the module default is Enabled
    geoRedundantBackup: 'Disabled'

    // decision: postgresql-flexible-server.server.databases
    databases: [
      { name: 'app', charset: 'UTF8', collation: 'en_US.utf8' }
    ]

    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'PostgreSQLLogs' }
          { category: 'PostgreSQLFlexSessions' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = postgresql.outputs.resourceId
output fqdn string = postgresql.outputs.?fqdn ?? ''
```

A burstable size sets `tier: 'Burstable'`, `skuName: 'Standard_B2s'` and `highAvailability: 'Disabled'`. A
customer-managed key adds `customerManagedKey` and a user-assigned identity in `managedIdentities`; a
VNet-integrated server drops `privateEndpoints` for `delegatedSubnetResourceId` and
`privateDnsZoneArmResourceId`.

### Database roles

Entra roles are created inside the server, as the Entra administrator:
`pgaadauth_create_principal('name', false, false)` and a `GRANT`. No ARM resource does it; it is a
step after the deployment, recorded in the spec as `database_roles`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the
databases, the administrators and the configurations. `database_roles` and the Defender plan are
`not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.DBforPostgreSQL/flexibleServers`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Property |
|---|---|
| `availability_zone` (not a question of the set) | `properties.availabilityZone` |
