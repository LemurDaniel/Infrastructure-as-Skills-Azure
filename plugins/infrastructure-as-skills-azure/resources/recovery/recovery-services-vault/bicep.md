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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
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
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.RecoveryServices/vaults` with `sku: { name: 'RS0', tier: 'Standard' }`
and `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
