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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide parameters, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
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
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Compute/virtualMachines` with a `Microsoft.Network/networkInterfaces`
beside it.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
