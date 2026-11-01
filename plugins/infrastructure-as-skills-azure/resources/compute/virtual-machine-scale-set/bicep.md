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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide parameters, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
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
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Compute/virtualMachineScaleSets` with `sku`, `zones` and
`properties.orchestrationMode`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
