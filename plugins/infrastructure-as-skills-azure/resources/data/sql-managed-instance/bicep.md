# Rendering an Azure SQL Managed Instance as Bicep

Mapping from the question set to the instance and its databases. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/sql-managed-instance.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/sql/managed-instance:<version>` | **0.5.1** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
builds the instance, its databases with their retention policies, keys and the encryption
protector, the security alert policy and the classic vulnerability assessment, role assignments
and a **logs-only** diagnostic setting. It has **no private endpoint parameter**, no metrics, no
threat-protection setting without a storage account, no audit and no NSG rule.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `service_tier`, `hardware_family` | `skuTier: 'GeneralPurpose' / 'BusinessCritical'`, `skuName: 'GP_Gen5'` (`GP_Gen8IM`, `GP_Gen8IH`, `BC_...`), `hardwareFamily: 'Gen5' / 'Gen8IM' / 'Gen8IH'` | Three parameters; the defaults are `GP_Gen5` / `GeneralPurpose` / `Gen5`; written |
| `vcores` | `vCores` | Default `4`; written |
| `storage_gb` | `storageSizeInGB` | Default `32`; a multiple of 32; written |
| `license_type` | `licenseType` | Default `LicenseIncluded`; written |
| `collation` | `collation` | Fixed at creation |
| `timezone` | `timezoneId` | Fixed at creation |
| `maintenance_window` | `maintenanceWindow: 'SystemManaged' / 'Custom1' (weekday nights) / 'Custom2' (weekend nights)` | The module resolves the region's configuration id |
| `databases` | `databases: [ { name, ... } ]` | |
| `zone_redundant` | `zoneRedundant` | Module default **`false`**; written |
| `geo_failover_region` | **not one call** - a second instance with `dnsZonePartnerResourceId` and an authored `Microsoft.Sql/locations/instanceFailoverGroups` | |
| `subnet` | `subnetResourceId` | Required; fixed at creation |
| `public_data_endpoint` | `publicDataEndpointEnabled` | Bool, default `false`; written |
| `ip_rules` | **not the module** - a `securityRules` entry (3342) on the subnet's NSG | Open entry when the platform owns the NSG |
| `private_endpoint`, `private_endpoint_subnet` | **not the module** - an authored `Microsoft.Network/privateEndpoints` with `groupIds: ['managedInstance']` | |
| `connection_type` | `proxyOverride` | Module default **`Proxy`**; written |
| `minimum_tls_version` | `minimalTlsVersion: '1.2'` | Written |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }`, `primaryUserAssignedIdentityResourceId` | The primary id is required with a user-assigned identity |
| `entra_admin`, `local_authentication_disabled` | `administrators: { azureADOnlyAuthentication: true, login, sid, principalType: 'Group', tenantId }` and **no** `administratorLogin` / `administratorLoginPassword` | The module makes the pair conditional on `administrators` being absent |
| `database_users` | **not the module** | T-SQL after the deployment |
| `role_assignments` | `roleAssignments` | Control plane |
| `key_management`, `cmk_key_vault_key_id` | `keys: [ { name: '<vault>_<key>_<version>', serverKeyType: 'AzureKeyVault', uri } ]` and `encryptionProtector: { serverKeyName, serverKeyType: 'AzureKeyVault', autoRotationEnabled: true }` | |
| `threat_detection` | **not the module** (`securityAlertPolicy` wants a storage account when enabled) - an authored `advancedThreatProtectionSettings/Default` | |
| `vulnerability_assessment`, `vulnerability_assessment_storage_account` | `vulnerabilityAssessment: { name: 'default', storageAccountResourceId, createStorageRoleAssignment: true, recurringScans: { isEnabled: true } }` | Classic form; unset when off |
| `short_term_retention_days` | `databases[].backupShortTermRetentionPolicy: { retentionDays }` | |
| `long_term_retention` | `databases[].backupLongTermRetentionPolicy: { weeklyRetention }` | `'P13W'`, `'P52W'` |
| `backup_storage_redundancy` | `requestedBackupStorageRedundancy` | Module default **`Geo`**; written; all four values |
| `diagnostic_workspace`, `diagnostic_categories` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ] } ]` | **Logs only** - the type has no `metricCategories` |
| `metrics_enabled` | **not the module** - a second, authored `Microsoft.Insights/diagnosticSettings` with `metrics: [ { category: 'AllMetrics' } ]` | |
| `auditing_enabled` | **not the module** - T-SQL, plus `SQLSecurityAuditEvents` above | |
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module sqlmi 'br/public:avm/res/sql/managed-instance:0.5.1' = {
  name: 'sql-managed-instance'
  params: {
    name: sqlmiName
    location: location
    tags: tags

    // decision: sql-managed-instance.instance.service_tier / hardware_family
    skuName: 'GP_Gen5'
    skuTier: 'GeneralPurpose'
    hardwareFamily: 'Gen5'
    // decision: sql-managed-instance.instance.vcores
    vCores: 4
    // decision: sql-managed-instance.instance.storage_gb
    storageSizeInGB: 256
    // decision: sql-managed-instance.instance.license_type
    licenseType: 'LicenseIncluded'
    // decision: sql-managed-instance.instance.collation
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    // decision: sql-managed-instance.instance.timezone
    timezoneId: 'UTC'
    // decision: sql-managed-instance.instance.maintenance_window
    maintenanceWindow: 'Custom1'

    // decision: sql-managed-instance.resilience.zone_redundant - the module default is false
    zoneRedundant: true

    // decision: sql-managed-instance.networking.subnet
    subnetResourceId: subnetId
    // decision: sql-managed-instance.networking.public_data_endpoint
    publicDataEndpointEnabled: false
    // decision: sql-managed-instance.networking.connection_type - the module default is Proxy
    proxyOverride: 'Redirect'
    // decision: sql-managed-instance.networking.minimum_tls_version
    minimalTlsVersion: '1.2'

    // decision: sql-managed-instance.identity.managed_identity
    managedIdentities: { systemAssigned: true }
    // decision: sql-managed-instance.identity.entra_admin / security.local_authentication_disabled
    // Entra-only: no administratorLogin, no password
    administrators: {
      azureADOnlyAuthentication: true
      login: entraAdminLogin
      sid: entraAdminObjectId
      principalType: 'Group'
      tenantId: tenantId
    }

    // decision: sql-managed-instance.data_protection.backup_storage_redundancy - the module default is Geo
    requestedBackupStorageRedundancy: 'Zone'

    // decision: sql-managed-instance.instance.databases
    databases: [
      {
        name: 'app'
        // decision: sql-managed-instance.data_protection.short_term_retention_days
        backupShortTermRetentionPolicy: { retentionDays: 7 }
        // decision: sql-managed-instance.data_protection.long_term_retention
        backupLongTermRetentionPolicy: { weeklyRetention: 'P13W' }
      }
    ]

    // decision: sql-managed-instance.observability.diagnostic_workspace / diagnostic_categories
    // (metrics_enabled: the module's setting carries logs only - the metrics setting is authored below)
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ResourceUsageStats' }
          { category: 'SQLSecurityAuditEvents' }
          { category: 'DevOpsOperationsAudit' }
        ]
      }
    ]

    // decision: sql-managed-instance.identity.role_assignments
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

resource instance 'Microsoft.Sql/managedInstances@2024-05-01-preview' existing = {
  name: sqlmiName
  dependsOn: [ sqlmi ]
}

// decision: sql-managed-instance.security.threat_detection - the module's securityAlertPolicy wants a storage account
resource threatProtection 'Microsoft.Sql/managedInstances/advancedThreatProtectionSettings@2024-05-01-preview' = {
  parent: instance
  name: 'Default'
  properties: { state: 'Enabled' }
}

// decision: sql-managed-instance.observability.metrics_enabled - a second setting, metrics only
resource metricsDiagnostic 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'metrics'
  scope: instance
  properties: {
    workspaceId: diagnosticWorkspaceId
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output id string = sqlmi.outputs.resourceId
output name string = sqlmi.outputs.name
```

Validated with `bicep build` against 0.5.1 (no warnings). A customer-managed key adds
`managedIdentities: { userAssignedResourceIds: [identityId] }`, `primaryUserAssignedIdentityResourceId`,
`keys: [ { name: '${vaultName}_${keyName}_${keyVersion}', serverKeyType: 'AzureKeyVault', uri: keyUri } ]`
and `encryptionProtector: { serverKeyName: '${vaultName}_${keyName}_${keyVersion}', serverKeyType: 'AzureKeyVault', autoRotationEnabled: true }`.

### The private endpoint, the public endpoint rule, the audit and the users

A private endpoint for a caller in an unpeered network is an authored
`Microsoft.Network/privateEndpoints` on `instance.id` with `groupIds: ['managedInstance']` in the
deployment's endpoint subnet, and no `privateDnsZoneGroup` under `private_dns_records: policy`.
`enabled_with_firewall` is a security rule (TCP 3342 from `ip_rules`) on the subnet's NSG, rendered
only when this deployment owns it. The server audit (`CREATE SERVER AUDIT ... TO EXTERNAL_MONITOR`)
and the logins (`CREATE LOGIN ... FROM EXTERNAL PROVIDER`, then users and roles per database) are
T-SQL after the deployment, from inside the network; the spec records `auditing_enabled` and
`database_users` as that step.

### A second region

`geo_failover_region` is a second instance of this module in that region with
`dnsZonePartnerResourceId: sqlmi.outputs.resourceId`, and an authored
`Microsoft.Sql/locations/instanceFailoverGroups` in the primary's region naming both instances. The
exact shape is read from the ARM reference at render time.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every module-carried decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the SKU triple,
cores, storage, licence, collation, time zone, maintenance window, zone redundancy, the subnet,
the public endpoint, the proxy override, TLS, the administrators object, backup redundancy, the
databases' retention and the diagnostic categories. The threat-protection setting and the metrics
setting are top-level resources of the compiled template. `database_users`, the audit's T-SQL half,
an NSG rule on a platform NSG and the Defender plan are `not-testable` (not a resource of this
template).

## Authored rendering

The fallback. `Microsoft.Sql/managedInstances`:

| Decision | Property |
|---|---|
| the instance | `sku { name, tier, family, capacity }`, `properties.vCores`, `storageSizeInGB`, `licenseType`, `collation`, `timezoneId`, `maintenanceConfigurationId`, `zoneRedundant`, `subnetId`, `publicDataEndpointEnabled`, `proxyOverride`, `minimalTlsVersion`, `requestedBackupStorageRedundancy`, `dnsZonePartner` |
| `entra_admin`, `local_authentication_disabled` | `properties.administrators { administratorType: 'ActiveDirectory', azureADOnlyAuthentication, login, sid, principalType, tenantId }`, no `administratorLogin` |
| `managed_identity` | `identity { type, userAssignedIdentities }`, `properties.primaryUserAssignedIdentityId` |
| `key_management` | child `keys` and `encryptionProtector/current` |
| `threat_detection` | child `advancedThreatProtectionSettings/Default` |
| `vulnerability_assessment` | child `vulnerabilityAssessments/default` with `storageContainerPath` |
| `databases`, retention | child `databases`, `databases/backupShortTermRetentionPolicies/default`, `databases/backupLongTermRetentionPolicies/default` |
| `ip_rules` | a `securityRules` entry on the subnet's NSG |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: ['managedInstance']` |
| `geo_failover_region` | `Microsoft.Sql/locations/instanceFailoverGroups` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` with `logs: [ { category } ]` and `metrics: [ { category: 'AllMetrics' } ]` |
