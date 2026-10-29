# Rendering a Virtual Machine as Bicep

Mapping from the question set to the machine. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/virtual-machine.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/compute/virtual-machine:<version>` | **0.22.3** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `os_type` | `osType: 'Linux'` / `'Windows'` | Required |
| `image` | `imageReference: { publisher, offer, sku, version: 'latest' }` | A gallery image: `imageReference: { id }` |
| `instance_count` | a module loop `[for i in range(1, count): ...]` | Each name with the instance number |
| `size` | `vmSize` | Required; written |
| `license_type` | `licenseType: 'Windows_Server'` | |
| `availability`, `zone` | `availabilityZone: 1` (`-1` for none), `availabilitySetResourceId` | `availabilityZone` is **required**; `-1` when a set or no zone |
| `os_disk_storage`, `os_disk_size_gb`, `disk_encryption_set_id` | `osDisk: { caching, createOption: 'FromImage', deleteOption: 'Delete', diskSizeGB, managedDisk: { storageAccountType, diskEncryptionSetResourceId } }` | `deleteOption: 'Delete'` so a rebuild leaves no orphan disk |
| `data_disks` | `dataDisks` | Same zone as the machine |
| `workload_subnet`, `public_ip`, `private_ip_allocation`, `accelerated_networking` | `nicConfigurations: [ { enableAcceleratedNetworking, ipConfigurations: [ { name, subnetResourceId, privateIPAllocationMethod } ] } ]` | No `pipConfiguration` is no public IP |
| `system_assigned_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | The Entra extension forces the system-assigned identity on |
| `entra_login` | `extensionAadJoinConfig: { enabled: true }` | The module picks `AADLoginForWindows` or `AADSSHLoginforLinux` by `osType`; `settings.mdmId` would enrol in Intune - left out |
| `role_assignments` | `roleAssignments` | |
| `trusted_launch` | `securityType: 'TrustedLaunch'`, `secureBootEnabled`, `vTpmEnabled` | Module defaults: no security type, both `false`; written |
| `encryption_at_host` | `encryptionAtHost` | Module default **`false`** (Terraform on); written |
| `admin_username`, `password_authentication`, `ssh_public_key` | `adminUsername`, `disablePasswordAuthentication: true`, `publicKeys: [ { keyData, path } ]` | Linux. Module default `disablePasswordAuthentication` is `false`; written |
| `credential_key_vault` | `adminPassword: getSecret(...)` in the parameter file | Windows: a Key Vault reference, never a literal; the module takes it as `string` |
| `backup_enabled`, `backup_vault_id`, `backup_policy_id` | `backupVaultName`, `backupVaultResourceGroup`, `backupPolicyName` | Policy **name**, default `DefaultPolicy`; empty vault name is no backup |
| `patch_mode` | `patchMode: 'AutomaticByPlatform'`, `patchAssessmentMode: 'AutomaticByPlatform'` | Module defaults `''` and `'ImageDefault'`; written |
| `auto_shutdown*` | `autoShutdownConfig: { status: 'Enabled', dailyRecurrenceTime: '1900', timeZone, notificationSettings: { status: 'Disabled' } }` | `{}` is none; time is `HHmm` |
| `boot_diagnostics` | `bootDiagnostics: true` | Managed storage account; module default `false`; written |
| `diagnostic_*`, `metrics_enabled` | `nicConfigurations[].diagnosticSettings: [ { workspaceResourceId, metricCategories: [ { category: 'AllMetrics' } ] } ]` | The module has no machine-level diagnostic setting; metrics go on the interface |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call (Linux)

```bicep
module vm 'br/public:avm/res/compute/virtual-machine:0.22.3' = {
  name: 'virtual-machine'
  params: {
    name: vmName
    location: location
    tags: tags
    // decision: virtual-machine.machine.availability - one machine in a zone is placement, not redundancy
    availabilityZone: 1

    osType: 'Linux'
    vmSize: 'Standard_D2ds_v5'
    imageReference: {
      publisher: 'Canonical'
      offer: 'ubuntu-24_04-lts'
      sku: 'server'
      version: 'latest'
    }
    // decision: virtual-machine.machine.os_disk_storage
    osDisk: {
      caching: 'ReadWrite'
      createOption: 'FromImage'
      deleteOption: 'Delete'
      diskSizeGB: 64
      managedDisk: {
        storageAccountType: 'Premium_ZRS'
        diskEncryptionSetResourceId: diskEncryptionSetId // customer_managed only
      }
    }

    nicConfigurations: [
      {
        enableAcceleratedNetworking: true
        ipConfigurations: [
          {
            name: 'ipconfig01'
            subnetResourceId: workloadSubnetId
            // decision: virtual-machine.networking.public_ip - no pipConfiguration, no public IP
          }
        ]
        diagnosticSettings: [
          {
            workspaceResourceId: diagnosticWorkspaceId
            metricCategories: [ { category: 'AllMetrics' } ]
          }
        ]
      }
    ]

    // decision: virtual-machine.security.password_authentication - the module default is false
    adminUsername: 'azureuser'
    disablePasswordAuthentication: true
    publicKeys: [
      {
        keyData: adminSshPublicKey
        path: '/home/azureuser/.ssh/authorized_keys'
      }
    ]

    // decision: virtual-machine.security.encryption_at_host - the Terraform default is on
    securityType: 'TrustedLaunch'
    secureBootEnabled: true
    vTpmEnabled: true
    encryptionAtHost: true
    patchMode: 'AutomaticByPlatform'
    patchAssessmentMode: 'AutomaticByPlatform'
    bootDiagnostics: true

    managedIdentities: { systemAssigned: true }
    extensionAadJoinConfig: { enabled: true }

    autoShutdownConfig: {
      status: 'Enabled'
      dailyRecurrenceTime: '1900'
      timeZone: 'UTC'
      notificationSettings: { status: 'Disabled' }
    }

    backupVaultName: backupVaultName
    backupPolicyName: backupPolicyName

    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = vm.outputs.resourceId
output principalId string = vm.outputs.?systemAssignedMIPrincipalId ?? ''
```

A Windows machine differs in `osType: 'Windows'`, the image, `osDisk.diskSizeGB: 128`,
`licenseType`, no `publicKeys`, and `adminPassword` from a Key Vault reference. The Linux call
was built with `bicep build` against 0.22.3. A zone-less machine passes
`availabilityZone: -1`; the shutdown time format `1900` is what the schedule resource takes,
where the module's own default is written `19:00` - check the first deployment.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Compute/virtualMachines` with a `Microsoft.Network/networkInterfaces`
beside it:

| Decision | Property |
|---|---|
| `image`, `size` | `properties.storageProfile.imageReference`, `properties.hardwareProfile.vmSize` |
| `availability`, `zone` | `zones: [ '1' ]`, `properties.availabilitySet.id` |
| `os_disk_storage`, `os_disk_size_gb` | `properties.storageProfile.osDisk { managedDisk.storageAccountType, diskSizeGB, managedDisk.diskEncryptionSet.id }` |
| `trusted_launch`, `encryption_at_host` | `properties.securityProfile { securityType, uefiSettings { secureBootEnabled, vTpmEnabled }, encryptionAtHost }` |
| `admin_username`, `password_authentication`, `ssh_public_key` | `properties.osProfile { adminUsername, linuxConfiguration { disablePasswordAuthentication, ssh.publicKeys } }` |
| `patch_mode` | `osProfile.linuxConfiguration.patchSettings { patchMode, assessmentMode }` |
| `system_assigned_identity`, `user_assigned_identity_ids` | `identity { type, userAssignedIdentities }` |
| `entra_login` | child `extensions` (`AADSSHLoginForLinux` / `AADLoginForWindows`) |
| `boot_diagnostics` | `properties.diagnosticsProfile.bootDiagnostics.enabled` |
| `auto_shutdown` | `Microsoft.DevTestLab/schedules` (`shutdown-computevm-<name>`) |
| `backup_*` | `Microsoft.RecoveryServices/vaults/backupFabrics/protectionContainers/protectedItems` |
| `public_ip`, `workload_subnet` | `networkInterfaces.properties.ipConfigurations[].properties.subnet.id`; no `publicIPAddress` |
