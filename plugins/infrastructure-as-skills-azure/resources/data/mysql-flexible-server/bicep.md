# Rendering a MySQL Flexible Server as Bicep

Mapping from the question set to the server. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/mysql-flexible-server.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/db-for-my-sql/flexible-server:<version>` | **0.11.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `mysql_version` | `version` | Allowed `'5.7'`, `'8.0.21'`, `'8.4'`, `'9.3'`; module default **`'8.0.21'`**; written |
| `compute_tier`, `sku_name` | `tier: 'GeneralPurpose'` and `skuName: 'Standard_D2ds_v4'` | Two parameters that must agree; both required |
| `storage_size_gb` | `storageSizeGB` | Only the listed sizes; default 64; written |
| `storage_auto_grow` | `storageAutoGrow` | Module default **`'Disabled'`**; written |
| `databases` | `databases: [ { name, charset, collation } ]` | |
| `high_availability` | `highAvailability: 'ZoneRedundant'` / `'SameZone'` / `'Disabled'` | Default `'ZoneRedundant'`; written. `'Disabled'` on burstable |
| `availability_zone` | `availabilityZone: -1` | **Required** by the module; `-1` is no preference |
| `maintenance_window` | `maintenanceWindow: { customWindow: 'Enabled', dayOfWeek: 0, startHour: 2, startMinute: 0 }` | Module default `{}` |
| `private_connectivity: private_endpoint` | `privateEndpoints`, with `delegatedSubnetResourceId` and `privateDnsZoneResourceId` unset | |
| `private_connectivity: vnet_integration` | `delegatedSubnetResourceId`, `privateDnsZoneResourceId` | Fixed at creation |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` | Default disabled; written |
| `ip_rules`, `allow_azure_services` | `firewallRules: [ { name, startIpAddress, endIpAddress } ]` | |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'mysqlServer' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | User-assigned only; no system-assigned form |
| `entra_admin` | `administrators: [ { identityResourceId, login, sid } ]` | |
| `password_authentication_disabled` | `configurations: [ { name: 'aad_auth_only', source: 'user-override', value: 'ON' } ]` | The administrator login and a secure password are still required at creation |
| `database_users` | **not the module** | SQL after the deployment |
| `role_assignments` | `roleAssignments` | Control plane |
| `minimum_tls_version` | `configurations` `tls_version` = `'TLSv1.2,TLSv1.3'` (or `'TLSv1.3'`) and `require_secure_transport` = `'ON'` | A list, not a minimum |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, userAssignedIdentityResourceId }` | Unversioned |
| `threat_protection` | `advancedThreatProtection: 'Enabled'` | Default `'Enabled'`; written |
| `audit_logging` | `configurations` `audit_log_enabled` = `'ON'`, `audit_log_events` = `'CONNECTION'` | And the category below |
| `backup_retention_days` | `backupRetentionDays` | Default 7; written |
| `geo_redundant_backup` | `geoRedundantBackup: 'Enabled'` / `'Disabled'` | Module default **`'Enabled'`**; written |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
// The administrator password MySQL demands at creation, though Entra-only never uses it: generated for
// this deployment, secure, in no output and no state of ours.
@secure()
param mysqlBootstrapPassword string = '${newGuid()}Aa1!'

module mysql 'br/public:avm/res/db-for-my-sql/flexible-server:0.11.1' = {
  name: 'mysql-flexible-server'
  params: {
    name: mysqlName
    location: location
    tags: tags

    // decision: mysql-flexible-server.server.mysql_version / compute_tier / sku_name - the module default version is 8.0.21
    version: '8.4'
    tier: 'GeneralPurpose'
    skuName: 'Standard_D2ds_v4'
    // decision: mysql-flexible-server.server.storage_size_gb / storage_auto_grow - the module default is Disabled
    storageSizeGB: 64
    storageAutoGrow: 'Enabled'
    availabilityZone: -1

    // decision: mysql-flexible-server.security.password_authentication_disabled
    // Entra-only (aad_auth_only below); the account MySQL requires is never used
    administratorLogin: 'mysqladmin'
    administratorLoginPassword: mysqlBootstrapPassword

    // decision: mysql-flexible-server.identity.user_assigned_identity_ids / entra_admin
    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    administrators: [
      {
        identityResourceId: userAssignedIdentityId
        login: entraAdminName
        sid: entraAdminObjectId
      }
    ]

    // decision: mysql-flexible-server.resilience.high_availability
    highAvailability: 'ZoneRedundant'
    // decision: mysql-flexible-server.resilience.maintenance_window
    maintenanceWindow: {
      customWindow: 'Enabled'
      dayOfWeek: 0
      startHour: 2
      startMinute: 0
    }

    // decision: mysql-flexible-server.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    firewallRules: []
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'mysqlServer'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: mysql-flexible-server.security.minimum_tls_version / password_authentication_disabled
    // decision: mysql-flexible-server.observability.audit_logging
    configurations: [
      { name: 'aad_auth_only', source: 'user-override', value: 'ON' }
      { name: 'tls_version', source: 'user-override', value: 'TLSv1.2,TLSv1.3' }
      { name: 'require_secure_transport', source: 'user-override', value: 'ON' }
      { name: 'audit_log_enabled', source: 'user-override', value: 'ON' }
      { name: 'audit_log_events', source: 'user-override', value: 'CONNECTION' }
    ]
    // decision: mysql-flexible-server.security.threat_protection
    advancedThreatProtection: 'Enabled'

    // decision: mysql-flexible-server.data_protection.backup_retention_days
    backupRetentionDays: 7
    // decision: mysql-flexible-server.data_protection.geo_redundant_backup - the module default is Enabled
    geoRedundantBackup: 'Disabled'

    // decision: mysql-flexible-server.server.databases
    databases: [
      { name: 'app', charset: 'utf8mb4', collation: 'utf8mb4_0900_ai_ci' }
    ]

    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [ { category: 'MySqlAuditLogs' } ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = mysql.outputs.resourceId
output fqdn string = mysql.outputs.?fqdn ?? ''
```

A burstable size sets `tier: 'Burstable'`, `skuName: 'Standard_B2s'` and `highAvailability: 'Disabled'`. A
customer-managed key adds `customerManagedKey`; a VNet-integrated server drops `privateEndpoints` for
`delegatedSubnetResourceId` and `privateDnsZoneResourceId`.

### Database users

Entra users are created inside the server, as the Entra administrator: `CREATE AADUSER 'name'
IDENTIFIED BY '<client id>'` and a `GRANT`. No ARM resource does it; it is a step after the
deployment, recorded in the spec as `database_users`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)), including the
databases, the administrator and the configurations. `database_users` and the Defender plan are
`not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.DBforMySQL/flexibleServers`:

| Decision | Property |
|---|---|
| `mysql_version`, `compute_tier`, `sku_name` | `properties.version`, `sku { name, tier }` |
| `storage_size_gb`, `storage_auto_grow` | `properties.storage { storageSizeGB, autoGrow }` |
| `high_availability`, `availability_zone` | `properties.highAvailability { mode }`, `properties.availabilityZone` |
| `maintenance_window` | `properties.maintenanceWindow` |
| `public_network_access` | `properties.network.publicNetworkAccess`, child `firewallRules` |
| `private_connectivity: vnet_integration` | `properties.network { delegatedSubnetResourceId, privateDnsZoneResourceId }` |
| `private_connectivity: private_endpoint` | `Microsoft.Network/privateEndpoints` with `groupIds: ['mysqlServer']` |
| `user_assigned_identity_ids` | `identity { type: 'UserAssigned', userAssignedIdentities }` |
| `entra_admin` | child `administrators` |
| `password_authentication_disabled`, `minimum_tls_version`, `audit_logging` | child `configurations` |
| `key_management` | `properties.dataEncryption` |
| `backup_retention_days`, `geo_redundant_backup` | `properties.backup { backupRetentionDays, geoRedundantBackup }` |
| `databases` | child `databases` |
| `threat_protection` | child `advancedThreatProtectionSettings/Default` |
