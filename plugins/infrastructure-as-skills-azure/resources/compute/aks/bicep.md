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

| Decision | Parameter | Note |
|---|---|---|
| `sku_tier` | `skuTier` | Default `'Standard'` (Terraform: unset); written. `skuName` stays `'Base'` |
| `kubernetes_version` | `kubernetesVersion` | |
| `upgrade_channel`, `node_os_upgrade_channel` | `autoUpgradeProfile: { upgradeChannel, nodeOSUpgradeChannel }` | Default channel **`'stable'`** (Terraform: `none`); written |
| `zone_redundant` | `availabilityZones: [ 1, 2, 3 ]` on both pool profiles | Integers here, strings in Terraform |
| `public_network_access` | `publicNetworkAccess` and `apiServerAccessProfile.enablePrivateCluster` | Default `'Disabled'`; written |
| `authorized_ip_ranges` | `apiServerAccessProfile.authorizedIPRanges` | Never rendered empty |
| `private_dns_zone`, `private_dns_zone_id` | `apiServerAccessProfile.privateDNSZone` | `'system'` or the zone's resource id |
| `node_subnet` | `vnetSubnetResourceId` on each pool profile | |
| `network_plugin_mode` | `networkPlugin: 'azure'`, `networkPluginMode` | `'overlay'`, or unset for `vnet` |
| `network_dataplane`, `network_policy` | `networkDataplane`, `networkPolicy` | `'cilium'` / `'azure'`; policy `'cilium'`, `'calico'`, `'azure'` |
| `pod_cidr`, `service_cidr`, `dns_service_ip` | `podCidr`, `serviceCidr`, `dnsServiceIP` | `podCidr` only with overlay |
| `outbound_type` | `outboundType` | Default `'loadBalancer'`; written |
| `system_pool_*`, `system_pool_dedicated` | `primaryAgentPoolProfiles: [ { name, mode: 'System', vmSize, enableAutoScaling, count, minCount, maxCount, nodeTaints } ]` | `count` is the initial size, written equal to `minCount` |
| `user_pool_*` | `agentPools: [ { name, mode: 'User', vmSize, enableAutoScaling, count, minCount, maxCount } ]` | |
| `os_sku`, `os_disk_type` | `osSKU`, `osDiskType` on each pool profile | Release names (`AzureLinux3`, ...) from the README |
| `encryption_at_host` | `enableEncryptionAtHost` on each pool profile | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | System- or user-assigned, **not both** |
| `entra_integration`, `azure_rbac_enabled`, `admin_group_object_ids` | `aadProfile: { managed, enableAzureRBAC, adminGroupObjectIDs }` | `enableRBAC: true` written beside it (default `true`) |
| `local_accounts_disabled` | `disableLocalAccounts` | Default `true` (Terraform: `false`); written |
| `oidc_issuer_enabled` | `enableOidcIssuerProfile` | Default **`false`**; written |
| `workload_identity_enabled` | `securityProfile.workloadIdentity: { enabled }` | |
| `defender_enabled` | `securityProfile.defender: { logAnalyticsWorkspaceResourceId, securityMonitoring: { enabled } }` | |
| `image_cleaner_enabled` | `securityProfile.imageCleaner: { enabled, intervalHours: 168 }` | |
| `azure_policy_enabled` | `azurePolicyEnabled` | Default `true`; written |
| `keyvault_secrets_provider_enabled` | `enableKeyvaultSecretsProvider`, `enableSecretRotation` | Defaults `false` / `false`; written |
| `key_management`, `disk_encryption_set_id` | `diskEncryptionSetResourceId` | |
| `container_insights_enabled` | `omsAgentEnabled`, `omsAgentUseAADAuth: true`, `monitoringWorkspaceResourceId` | Default `omsAgentEnabled: true`, AAD auth `false`; written |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `role_assignments` | `roleAssignments` | |
| `acr_pull_registry_ids` | *(root)* a `Microsoft.Authorization/roleAssignments` per registry for the `kubeletIdentityObjectId` output | Not a module parameter; `AcrPull` on the registry |
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
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the pool decisions
are members of the `primaryAgentPoolProfiles` and `agentPools` values.

## Authored rendering

The fallback. `Microsoft.ContainerService/managedClusters` with `sku` and `properties`:

| Decision | Property |
|---|---|
| `sku_tier` | `sku: { name: 'Base', tier }` |
| `kubernetes_version`, `upgrade_channel`, `node_os_upgrade_channel` | `properties.kubernetesVersion`, `properties.autoUpgradeProfile: { upgradeChannel, nodeOSUpgradeChannel }` |
| `public_network_access`, private cluster, DNS zone | `properties.publicNetworkAccess`, `properties.apiServerAccessProfile: { enablePrivateCluster, authorizedIPRanges, privateDNSZone }` |
| networking | `properties.networkProfile: { networkPlugin, networkPluginMode, networkDataplane, networkPolicy, podCidr, serviceCidr, dnsServiceIP, outboundType }` |
| the pools | `properties.agentPoolProfiles[]` with `mode`, `vmSize`, `enableAutoScaling`, `minCount`, `maxCount`, `availabilityZones`, `osSKU`, `osDiskType`, `enableEncryptionAtHost`, `vnetSubnetID`, `nodeTaints`; the user pool may be a child `agentPools` resource |
| identity | `identity: { type: 'UserAssigned', userAssignedIdentities }` |
| Entra, RBAC, local accounts | `properties.aadProfile`, `properties.enableRBAC`, `properties.disableLocalAccounts` |
| OIDC, workload identity, Defender, image cleaner | `properties.oidcIssuerProfile`, `properties.securityProfile: { workloadIdentity, defender, imageCleaner }` |
| add-ons | `properties.addonProfiles: { azurepolicy, omsagent, azureKeyvaultSecretsProvider }` |
| `key_management` | `properties.diskEncryptionSetID` |
