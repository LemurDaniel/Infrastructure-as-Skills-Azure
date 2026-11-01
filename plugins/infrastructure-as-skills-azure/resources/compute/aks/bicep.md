# Rendering AKS as Bicep

Mapping from the question set to the cluster and its two node pools. General layout, parameters
and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/aks.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/container-service/managed-cluster:<version>` | **0.14.0** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

Most parameters are typed from the ARM API (`resourceInput<'Microsoft.ContainerService/managedClusters@...'>`),
so nested objects use **ARM's camelCase names** (`apiServerAccessProfile.enablePrivateCluster`,
`aadProfile.adminGroupObjectIDs`), not module-invented ones. The cluster-wide network settings are
top-level parameters (`networkPlugin`, `podCidr`), the pools are `primaryAgentPoolProfiles` (the
system pool) and `agentPools`, and the OMS agent is switched by `omsAgentEnabled` together with
`monitoringWorkspaceResourceId`.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module cluster 'br/public:avm/res/container-service/managed-cluster:0.14.0' = {
  name: 'aks'
  params: {
    name: clusterName
    location: location
    tags: tags

    // decision: aks.cluster.sku_tier - Terraform's default is Free
    skuTier: 'Standard'
    kubernetesVersion: kubernetesVersion
    // decision: aks.cluster.upgrade_channel - Terraform's default channel is none
    autoUpgradeProfile: {
      upgradeChannel: 'patch'
      nodeOSUpgradeChannel: 'NodeImage'
    }

    // decision: aks.networking.public_network_access - a private cluster
    publicNetworkAccess: 'Disabled'
    apiServerAccessProfile: {
      enablePrivateCluster: true
      privateDNSZone: privateDnsZoneId // or 'system'
    }
    networkPlugin: 'azure'
    networkPluginMode: 'overlay'
    networkDataplane: 'cilium'
    networkPolicy: 'cilium'
    podCidr: '10.244.0.0/16'
    serviceCidr: serviceCidr
    dnsServiceIP: dnsServiceIp
    outboundType: 'userDefinedRouting'

    primaryAgentPoolProfiles: [
      {
        name: systemPoolName
        mode: 'System'
        vmSize: 'Standard_D4ds_v5'
        enableAutoScaling: true
        count: 3
        minCount: 3
        maxCount: 5
        // decision: aks.cluster.zone_redundant - fixed when the pool is created
        availabilityZones: [ 1, 2, 3 ]
        nodeTaints: [ 'CriticalAddonsOnly=true:NoSchedule' ]
        osSKU: 'AzureLinux'
        osDiskType: 'Ephemeral'
        enableEncryptionAtHost: true
        vnetSubnetResourceId: nodeSubnetId
      }
    ]
    agentPools: [
      {
        name: userPoolName
        mode: 'User'
        vmSize: 'Standard_D4ds_v5'
        enableAutoScaling: true
        count: 3
        minCount: 3
        maxCount: 10
        availabilityZones: [ 1, 2, 3 ]
        osSKU: 'AzureLinux'
        osDiskType: 'Ephemeral'
        enableEncryptionAtHost: true
        vnetSubnetResourceId: nodeSubnetId
      }
    ]

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    aadProfile: {
      managed: true
      enableAzureRBAC: true
      adminGroupObjectIDs: adminGroupObjectIds
    }
    enableRBAC: true
    // decision: aks.identity.local_accounts_disabled - inverse of local_auth
    disableLocalAccounts: true
    // decision: aks.identity.oidc_issuer_enabled - the module default is false
    enableOidcIssuerProfile: true
    securityProfile: {
      workloadIdentity: { enabled: true }
      imageCleaner: { enabled: true, intervalHours: 168 }
      defender: {
        logAnalyticsWorkspaceResourceId: diagnosticWorkspaceId
        securityMonitoring: { enabled: true }
      }
    }
    azurePolicyEnabled: true
    enableKeyvaultSecretsProvider: true
    enableSecretRotation: true
    omsAgentEnabled: true
    omsAgentUseAADAuth: true
    monitoringWorkspaceResourceId: diagnosticWorkspaceId

    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'kube-audit-admin' }
          { category: 'guard' }
          { category: 'cluster-autoscaler' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = cluster.outputs.resourceId
output oidcIssuerUrl string? = cluster.outputs.?oidcIssuerUrl
output kubeletIdentityObjectId string? = cluster.outputs.?kubeletIdentityObjectId
```

The call compiles with `bicep build` against 0.14.0 (the two output types are nullable in the
module). Pool names follow the `np` and `npsystem` abbreviations (`npsystem`, `npuser`) and are
lowercase alphanumeric, 12 characters at most. The identity's roles on the subnet and the DNS
zone are granted before the module is deployed, outside this call.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the pool decisions
are members of the `primaryAgentPoolProfiles` and `agentPools` values.

## Authored rendering

The fallback. `Microsoft.ContainerService/managedClusters` with `sku` and `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
