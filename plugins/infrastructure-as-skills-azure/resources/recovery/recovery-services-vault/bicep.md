# Rendering a Recovery Services vault as Bicep

Mapping from the question set to the vault. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/recovery-services-vault.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/recovery-services/vault:<version>` | **0.13.2** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `storage_redundancy`, `cross_region_restore` | `redundancySettings: { standardTierStorageRedundancy, crossRegionRestore }` | A discriminated object on `standardTierStorageRedundancy` (`GeoRedundant`, `LocallyRedundant`, `ZoneRedundant`); `crossRegionRestore` belongs to the `GeoRedundant` variant |
| `soft_delete`, `soft_delete_retention_days` | `softDeleteSettings: { softDeleteState, softDeleteRetentionPeriodInDays, enhancedSecurityState }` | All three required in the object; states `'Enabled'`, `'Disabled'`, `'AlwaysON'`, `'Invalid'` - write `'AlwaysON'` for both states for an `isolated` or `immutable` store |
| `immutability` | `immutabilitySettingState` | `'Disabled'`, `'Unlocked'`, `'Locked'`; written |
| `multi_user_authorization`, `resource_guard` | `resourceGuardOperationRequests` | The guard's operation-request ids; the vault's identity needs `Reader` on the guard |
| `job_failure_alerts` | `monitoringSettings` | Read the member names from the README; the alert setting is a member |
| `public_network_access` | `publicNetworkAccess` | `'Enabled'` / `'Disabled'`; module default **`'Disabled'`**; written |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'AzureBackup' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | A user-assigned key identity does not support private endpoints for backup |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `protected_resources` | `protectedItems` | |
| `backup_schedule`, `retention_days` | `backupPolicies` | Read the policy shape for the workload type from the README |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module recoveryVault 'br/public:avm/res/recovery-services/vault:0.13.2' = {
  name: 'recovery-services-vault'
  params: {
    name: recoveryVaultName
    location: location
    tags: tags

    // decision: recovery-services-vault.vault.storage_redundancy, cross_region_restore
    redundancySettings: {
      standardTierStorageRedundancy: 'ZoneRedundant'
    }
    // decision: recovery-services-vault.vault.soft_delete, soft_delete_retention_days
    softDeleteSettings: {
      softDeleteState: 'Enabled'
      softDeleteRetentionPeriodInDays: 14
      enhancedSecurityState: 'Enabled'
    }
    // decision: recovery-services-vault.vault.immutability
    immutabilitySettingState: 'Disabled'

    managedIdentities: {
      systemAssigned: true
    }

    // decision: recovery-services-vault.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'AzureBackup'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    backupPolicies: backupPolicies
    protectedItems: protectedItems

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'CoreAzureBackup' }
          { category: 'AddonAzureBackupJobs' }
          { category: 'AddonAzureBackupAlerts' }
          { category: 'AddonAzureBackupProtectedInstance' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = recoveryVault.outputs.resourceId
output principalId string = recoveryVault.outputs.systemAssignedMIPrincipalId
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.RecoveryServices/vaults` with `sku: { name: 'RS0', tier: 'Standard' }`
and `properties`:

| Decision | Property |
|---|---|
| `public_network_access` | `properties.publicNetworkAccess` |
| `storage_redundancy` | child `backupstorageconfig/vaultstorageconfig`: `properties.storageType`, `crossRegionRestoreFlag` |
| `soft_delete`, `immutability` | `properties.securitySettings: { softDeleteSettings, immutabilitySettings }` |
| `managed_identity` | `identity` (top level) |
| policies, protected items | child `backupPolicies`, `backupFabrics/protectionContainers/protectedItems` |
