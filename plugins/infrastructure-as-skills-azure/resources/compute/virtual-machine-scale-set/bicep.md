# Rendering a Virtual Machine Scale Set as Bicep

Mapping from the question set to the scale set. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/virtual-machine-scale-set.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/compute/virtual-machine-scale-set:<version>` | **0.11.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. This
module carries both orchestration modes, trusted launch and a metrics diagnostic setting.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `orchestration_mode` | `orchestrationMode: 'Flexible'` / `'Uniform'` | Default `'Flexible'`; written |
| `os_type` | `osType` | Required |
| `image` | `imageReference: { publisher, offer, sku, version: 'latest' }` | A gallery image: `imageReference: { id }` |
| `size`, `instances` | `skuName` (required), `skuCapacity` (default 1) | Written |
| `zones`, `zone_balance`, `fault_domain_count` | `availabilityZones: [ 1, 2, 3 ]`, `zoneBalance`, `scaleSetFaultDomain` | Defaults all three, `false`, 1; written |
| `os_disk_storage`, `os_disk_size_gb`, `disk_encryption_set_id` | `osDisk: { createOption: 'FromImage', caching, deleteOption: 'Delete', diskSizeGB, managedDisk: { storageAccountType, diskEncryptionSet: { id } } }` | A raw API object, not a module type |
| `upgrade_mode` | `upgradePolicyMode` | Default `'Manual'`; `'Rolling'` also sets the batch and unhealthy percentages (default 20 each) and `pauseTimeBetweenBatches`; written |
| `health_check_*` | `extensionHealthConfig: { enabled: true, protocol, port, requestPath }` | Module default is enabled on port 80, `/`; written |
| `instance_repair` | `automaticRepairsPolicyEnabled`, `gracePeriod` | Default on, `PT30M`; written |
| `workload_subnet`, `load_balancer_backend_pool_ids`, `accelerated_networking` | `nicConfigurations: [ { nicSuffix, enableAcceleratedNetworking, ipConfigurations: [ { name, properties: { subnet: { id }, loadBalancerBackendAddressPools: [ { id } ] } } ] } ]` | `ipConfigurations` is a free array of API objects; no `publicIPAddressConfiguration` is no public IP |
| `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | A Flexible set takes no system-assigned identity |
| `role_assignments` | `roleAssignments` | |
| `trusted_launch` | `securityType: 'TrustedLaunch'`, `secureBootEnabled`, `vTpmEnabled` | Module defaults empty, `false`, `false`; written |
| `encryption_at_host` | `encryptionAtHost` | Module default `true`; written |
| `admin_username`, `password_authentication`, `ssh_public_key` | `adminUsername`, `disablePasswordAuthentication`, `publicKeys: [ { keyData, path } ]` | `disablePasswordAuthentication` defaults to `false`; written. `adminPassword` is required: `''` for key-only Linux |
| `admin_password_secret` | `adminPassword` from `getSecret(...)` | Windows |
| `patch_mode` | `patchMode`, `patchAssessmentMode` | Module defaults `AutomaticByPlatform` and `ImageDefault`; written |
| `boot_diagnostics` | `bootDiagnosticEnabled` | Managed storage account when no account name is given |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, metricCategories: [ { category: 'AllMetrics' } ] } ]` | The type is metrics-only |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call (Linux)

```bicep
module vmss 'br/public:avm/res/compute/virtual-machine-scale-set:0.11.1' = {
  name: 'virtual-machine-scale-set'
  params: {
    name: vmssName
    location: location
    tags: tags

    // decision: virtual-machine-scale-set.scale_set.orchestration_mode
    orchestrationMode: 'Flexible'
    osType: 'Linux'
    skuName: 'Standard_D2ds_v5'
    skuCapacity: 2
    availabilityZones: [ 1, 2, 3 ]
    zoneBalance: false
    scaleSetFaultDomain: 1
    singlePlacementGroup: false

    imageReference: {
      publisher: 'Canonical'
      offer: 'ubuntu-24_04-lts'
      sku: 'server'
      version: 'latest'
    }
    osDisk: {
      createOption: 'FromImage'
      caching: 'ReadWrite'
      deleteOption: 'Delete'
      diskSizeGB: 64
      managedDisk: {
        storageAccountType: 'Premium_LRS'
        diskEncryptionSet: { id: diskEncryptionSetId } // customer_managed only
      }
    }

    // decision: virtual-machine-scale-set.security.password_authentication - the module default is false
    adminUsername: 'azureuser'
    adminPassword: ''
    disablePasswordAuthentication: true
    publicKeys: [
      {
        keyData: adminSshPublicKey
        path: '/home/azureuser/.ssh/authorized_keys'
      }
    ]

    nicConfigurations: [
      {
        nicSuffix: '-nic'
        enableAcceleratedNetworking: true
        ipConfigurations: [
          {
            name: 'ipconfig1'
            properties: {
              subnet: { id: workloadSubnetId }
              loadBalancerBackendAddressPools: [for id in loadBalancerBackendPoolIds: { id: id }]
              // decision: virtual-machine-scale-set.networking.public_ip - no publicIPAddressConfiguration
            }
          }
        ]
      }
    ]

    securityType: 'TrustedLaunch'
    secureBootEnabled: true
    vTpmEnabled: true
    encryptionAtHost: true
    patchMode: 'AutomaticByPlatform'
    patchAssessmentMode: 'AutomaticByPlatform'

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }

    upgradePolicyMode: 'Manual'
    automaticRepairsPolicyEnabled: true
    gracePeriod: 'PT30M'
    extensionHealthConfig: {
      enabled: true
      protocol: 'http'
      port: healthCheckPort
      requestPath: '/'
    }
    bootDiagnosticEnabled: true

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]

    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = vmss.outputs.resourceId
```

Built with `bicep build` against 0.11.1 (`healthCheckPort` was `80` in the built file). A Windows
set differs in `osType: 'Windows'`, the image, `osDisk.diskSizeGB: 128`, no `publicKeys`,
`adminPassword` from a Key Vault reference and the Windows patch settings. With
`orchestrationMode: 'Uniform'` the module applies `overprovision` and the single placement group
to the model; those are not decisions of this set and stay at the module's defaults.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Compute/virtualMachineScaleSets` with `sku`, `zones` and
`properties.orchestrationMode`:

| Decision | Property |
|---|---|
| `orchestration_mode`, `fault_domain_count`, `zone_balance` | `properties.orchestrationMode`, `properties.platformFaultDomainCount`, `properties.zoneBalance` |
| `size`, `instances` | `sku { name, capacity }` |
| `zones` | `zones: [ '1', '2', '3' ]` |
| `upgrade_mode`, `instance_repair` | `properties.upgradePolicy.mode`, `properties.automaticRepairsPolicy { enabled, gracePeriod }` |
| `image`, `os_disk_*` | `properties.virtualMachineProfile.storageProfile { imageReference, osDisk }` |
| `trusted_launch`, `encryption_at_host` | `properties.virtualMachineProfile.securityProfile { securityType, uefiSettings, encryptionAtHost }` |
| `admin_*`, `patch_mode` | `properties.virtualMachineProfile.osProfile { adminUsername, linuxConfiguration { disablePasswordAuthentication, ssh, patchSettings } }` |
| `workload_subnet`, `load_balancer_backend_pool_ids` | `virtualMachineProfile.networkProfile.networkInterfaceConfigurations` |
| `health_check_*` | `virtualMachineProfile.extensionProfile.extensions` (`ApplicationHealthLinux` / `ApplicationHealthWindows`) |
| `user_assigned_identity_ids` | `identity { type: 'UserAssigned', userAssignedIdentities }` |
| `boot_diagnostics` | `virtualMachineProfile.diagnosticsProfile.bootDiagnostics.enabled` |
