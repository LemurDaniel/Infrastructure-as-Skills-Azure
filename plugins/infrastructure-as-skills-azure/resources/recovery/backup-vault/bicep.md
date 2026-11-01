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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| (the datastore) | `dataStoreType` | Default `'VaultStore'`; written |
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
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The resource guard
proxy, outside the module, is matched as its own resource.

## Authored rendering

The fallback. `Microsoft.DataProtection/backupVaults` with `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
