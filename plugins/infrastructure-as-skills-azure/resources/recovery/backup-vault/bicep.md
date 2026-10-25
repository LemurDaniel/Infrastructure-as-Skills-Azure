# Rendering a Backup vault as Bicep

Mapping from the question set to the vault. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/backup-vault.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/data-protection/backup-vault:<version>` | **0.13.3** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `storage_redundancy` | `type` | `'GeoRedundant'` (module default), `'LocallyRedundant'`, `'ZoneRedundant'`; written |
| (the datastore) | `dataStoreType` | Default `'VaultStore'`; written |
| `cross_region_restore` | `featureSettings` | `crossRegionRestoreSettings.state`; read the member names from the README |
| `immutability` | `immutabilitySettingState` | `'Disabled'`, `'Unlocked'`, `'Locked'`; unset by default; written |
| `soft_delete_retention_days` | `softDeleteSettings: { state, retentionDurationInDays }` | `state` is `'AlwaysON'`, `'On'` or `'Off'`; write `'On'` with the days, `'AlwaysON'` for `isolated` and `immutable` |
| `multi_user_authorization`, `resource_guard` | - | **No parameter in this version.** The guard is attached with a `Microsoft.DataProtection/backupVaults/backupResourceGuardProxies` child resource outside the module, pointing at the guard id; the vault's identity needs `Reader` on the guard. Named in the handover |
| `infrastructure_encryption` | `infrastructureEncryption` | `'Enabled'` / `'Disabled'`; module default `'Enabled'`; written |
| `job_failure_alerts` | `azureMonitorAlertSettingsAlertsForAllJobFailures` | `'Enabled'` / `'Disabled'`; default `'Enabled'`; written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `protected_resources` | `backupInstances` | |
| `backup_schedule`, `retention_days` | `backupPolicies` | Read the policy shape for the datasource type from the README |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | - | **No `diagnosticSettings` parameter** in this version (the module's parameter list has `lock`, `customerManagedKey` and `featureSettings` but no diagnostics): a `Microsoft.Insights/diagnosticSettings` extension resource beside the module, below |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module backupVault 'br/public:avm/res/data-protection/backup-vault:0.13.3' = {
  name: 'backup-vault'
  params: {
    name: backupVaultName
    location: location
    tags: tags

    // decision: backup-vault.vault.storage_redundancy - the module default is GeoRedundant
    type: 'ZoneRedundant'
    dataStoreType: 'VaultStore'
    // decision: backup-vault.vault.immutability
    immutabilitySettingState: 'Disabled'
    // decision: backup-vault.vault.soft_delete_retention_days
    softDeleteSettings: {
      state: 'On'
      retentionDurationInDays: 14
    }
    infrastructureEncryption: 'Enabled'
    azureMonitorAlertSettingsAlertsForAllJobFailures: 'Enabled'

    managedIdentities: {
      systemAssigned: true
    }

    backupPolicies: backupPolicies
    backupInstances: backupInstances

    roleAssignments: roleAssignments

    enableTelemetry: true
  }
}

resource backupVaultRef 'Microsoft.DataProtection/backupVaults@2025-09-01' existing = {
  name: backupVaultName
  dependsOn: [ backupVault ]
}

// decision: backup-vault.observability.* - no diagnostics parameter on the module
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'workspace'
  scope: backupVaultRef
  properties: {
    workspaceId: diagnosticWorkspaceId
    logs: [
      { category: 'CoreAzureBackup', enabled: true }
      { category: 'AddonAzureBackupJobs', enabled: true }
      { category: 'AddonAzureBackupProtectedInstance', enabled: true }
    ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output id string = backupVault.outputs.resourceId
output principalId string = backupVault.outputs.systemAssignedMIPrincipalId
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The resource guard
proxy, outside the module, is matched as its own resource.

## Authored rendering

The fallback. `Microsoft.DataProtection/backupVaults` with `properties`:

| Decision | Property |
|---|---|
| `storage_redundancy` | `properties.storageSettings: [ { datastoreType: 'VaultStore', type } ]` |
| `cross_region_restore` | `properties.featureSettings.crossRegionRestoreSettings.state` |
| `immutability` | `properties.securitySettings.immutabilitySettings.state` |
| `soft_delete_retention_days` | `properties.securitySettings.softDeleteSettings: { state, retentionDurationInDays }` |
| `job_failure_alerts` | `properties.monitoringSettings.azureMonitorAlertSettings.alertsForAllJobFailures` |
| `managed_identity` | `identity` (top level) |
| policies, instances | child `backupPolicies`, `backupInstances` |
