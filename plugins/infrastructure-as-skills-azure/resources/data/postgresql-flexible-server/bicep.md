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

| Decision | Parameter | Note |
|---|---|---|
| `postgres_version` | `version` | A string; module default **`'18'`**; written |
| `compute_tier`, `sku_name` | `tier: 'GeneralPurpose'` and `skuName: 'Standard_D2ds_v5'` | Two parameters that must agree; both required |
| `storage_size_gb` | `storageSizeGB` | Default 32; written |
| `storage_auto_grow` | `autoGrow` | `'Enabled'` / `'Disabled'`; required |
| `databases` | `databases: [ { name, charset, collation } ]` | |
| `high_availability` | `highAvailability: 'ZoneRedundant'` / `'SameZone'` / `'Disabled'` | Default `'ZoneRedundant'`; written. `'Disabled'` on burstable |
| `availability_zone` | `availabilityZone: -1` | **Required** by the module; `-1` is no preference |
| `maintenance_window` | `maintenanceWindow: { customWindow: 'Enabled', dayOfWeek: 0, startHour: 2, startMinute: 0 }` | Module default 01:00; written |
| `private_connectivity: private_endpoint` | `privateEndpoints`, with `delegatedSubnetResourceId` and `privateDnsZoneArmResourceId` unset | Fixed at creation |
| `private_connectivity: vnet_integration` | `delegatedSubnetResourceId`, `privateDnsZoneArmResourceId` | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` | A string here, a bool in Terraform; default disabled; written |
| `ip_rules`, `allow_azure_services` | `firewallRules: [ { name, startIpAddress, endIpAddress } ]` | |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'postgresqlServer' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `managed_identity` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `entra_admins` | `administrators: [ { objectId, principalName, principalType: 'Group', tenantId } ]` | |
| `password_authentication_disabled` | `authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: 'Disabled', tenantId }` and **no** `administratorLogin`/`administratorLoginPassword` | Module default has Entra on and password off; written |
| `database_roles` | **not the module** | SQL after the deployment |
| `role_assignments` | `roleAssignments` | Control plane |
| `minimum_tls_version` | `configurations: [ { name: 'ssl_min_protocol_version', source: 'user-override', value: 'TLSv1.2' } ]` | |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, autoRotationEnabled: true, userAssignedIdentityResourceId }` | Unversioned |
| `threat_protection` | `enableAdvancedThreatProtection` | Default `true`; written |
| `backup_retention_days` | `backupRetentionDays` | Default 7; written |
| `geo_redundant_backup` | `geoRedundantBackup: 'Enabled'` / `'Disabled'` | Module default **`'Enabled'`** - differs from Terraform; written |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the
databases, the administrators and the configurations. `database_roles` and the Defender plan are
`not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.DBforPostgreSQL/flexibleServers`:

| Decision | Property |
|---|---|
| `postgres_version`, `compute_tier`, `sku_name` | `properties.version`, `sku { name, tier }` |
| `storage_size_gb`, `storage_auto_grow` | `properties.storage { storageSizeGB, autoGrow }` |
| `high_availability`, `availability_zone` | `properties.highAvailability { mode }`, `properties.availabilityZone` |
| `maintenance_window` | `properties.maintenanceWindow` |
| `public_network_access` | `properties.network.publicNetworkAccess`, child `firewallRules` |
| `private_connectivity: vnet_integration` | `properties.network { delegatedSubnetResourceId, privateDnsZoneArmResourceId }` |
| `private_connectivity: private_endpoint` | `Microsoft.Network/privateEndpoints` with `groupIds: ['postgresqlServer']` |
| `password_authentication_disabled` | `properties.authConfig { activeDirectoryAuth, passwordAuth, tenantId }` |
| `entra_admins` | child `administrators` |
| `minimum_tls_version` | child `configurations` |
| `key_management` | `properties.dataEncryption`, `identity` |
| `backup_retention_days`, `geo_redundant_backup` | `properties.backup { backupRetentionDays, geoRedundantBackup }` |
| `databases` | child `databases` |
| `threat_protection` | child `advancedThreatProtectionSettings/Default` |
