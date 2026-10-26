# Rendering an Azure Data Factory as Bicep

Mapping from the question set to the factory. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/data-factory.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/data-factory/factory:<version>` | **0.13.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
builds the factory, the managed virtual network with its managed private endpoints, the
integration runtimes (Managed and SelfHosted), the git binding, global parameters, private
endpoints of any service, the customer-managed key, role assignments, the lock and the diagnostic
setting - and linked services this plugin never renders (content).

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `managed_virtual_network` | `managedVirtualNetwork: { name: 'default' }` **and** `integrationRuntimes: [ { name, type: 'Managed', managedVirtualNetworkName: 'default', typeProperties: { computeProperties: { location: 'AutoResolve' } } } ]` | Omitted by default; written. The runtime is what runs inside the network |
| `managed_private_endpoints` | `managedVirtualNetwork.managedPrivateEndpoints: [ { name, privateLinkResourceId, groupId, fqdns } ]` | `fqdns` is required by the type; the source's endpoint host. Approval on the source follows |
| `self_hosted_integration_runtime` | `integrationRuntimes[] { name, type: 'SelfHosted' }` | The key is read with `listAuthKeys()` on the runtime after the deployment, into a Key Vault secret |
| `global_parameters` | `globalParameters: { <name>: { type, value } }` | An object keyed by name (a list in Terraform) |
| `purview_account` | `purviewResourceId` | Omitted for none |
| `git_provider: github` and details | `gitConfiguration: { type: 'FactoryGitHubConfiguration', accountName, repositoryName, collaborationBranch, rootFolder, hostName }` | The ARM `repoConfiguration` shape; omitted on every stage but development |
| `git_provider: azure_devops`, `git_project` | `gitConfiguration: { type: 'FactoryVSTSConfiguration', accountName, projectName, repositoryName, collaborationBranch, rootFolder, tenantId }` | |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` | A string; the module default is `''` (disabled only when endpoints are passed); written |
| `private_endpoint_subnet`, `private_endpoint_subresources` | `privateEndpoints: [ { service: 'dataFactory', subnetResourceId, name }, { service: 'portal', ... } ]` | Both services in one parameter |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoints | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned: true, userAssignedResourceIds }` | |
| `source_access` | **not the module** - role assignments beside the sources | Wiring |
| `role_assignments` | `roleAssignments` | Control plane |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, userAssignedIdentityResourceId, autoRotationEnabled: true }` | Unversioned with rotation |
| `diagnostic_workspace`, `diagnostic_categories`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | `logAnalyticsDestinationType` defaults to `Dedicated` |
| `deployment.resource_lock` | `lock` | Not on the lock list |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module adf 'br/public:avm/res/data-factory/factory:0.13.0' = {
  name: 'data-factory'
  params: {
    name: adfName
    location: location
    tags: tags

    // decision: data-factory.factory.managed_virtual_network - the module default is none
    managedVirtualNetwork: {
      name: 'default'
      // decision: data-factory.factory.managed_private_endpoints - one per source
      managedPrivateEndpoints: [
        {
          name: 'lake-dfs'
          privateLinkResourceId: lakeStorageAccountId
          groupId: 'dfs'
          fqdns: [ 'stlake.dfs.${environment().suffixes.storage}' ]
        }
      ]
    }
    integrationRuntimes: [
      {
        name: 'AutoResolveIntegrationRuntime'
        type: 'Managed'
        managedVirtualNetworkName: 'default'
        typeProperties: {
          computeProperties: { location: 'AutoResolve' }
        }
      }
      // decision: data-factory.factory.self_hosted_integration_runtime - none
    ]

    // decision: data-factory.factory.global_parameters
    globalParameters: {
      environment: { type: 'String', value: environmentName }
    }

    // decision: data-factory.factory.purview_account - none

    // decision: data-factory.source_control.git_provider - github, development stage only
    gitConfiguration: {
      type: 'FactoryGitHubConfiguration'
      accountName: gitAccount
      repositoryName: gitRepository
      collaborationBranch: 'main'
      rootFolder: '/'
      hostName: 'https://github.com'
    }

    // decision: data-factory.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: data-factory.networking.private_endpoint_subnet / private_endpoint_subresources
    privateEndpoints: [
      {
        name: 'pep-${adfName}-datafactory'
        service: 'dataFactory'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
      {
        name: 'pep-${adfName}-portal'
        service: 'portal'
        subnetResourceId: privateEndpointSubnetId
      }
    ]

    // decision: data-factory.identity.managed_identity
    managedIdentities: { systemAssigned: true }

    // decision: data-factory.security.key_management - platform managed: no customerManagedKey

    // decision: data-factory.observability.diagnostic_workspace / diagnostic_categories / metrics_enabled
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'PipelineRuns' }
          { category: 'ActivityRuns' }
          { category: 'TriggerRuns' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]

    // decision: data-factory.identity.role_assignments
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = adf.outputs.resourceId
output name string = adf.outputs.name
```

Validated with `bicep build` against 0.13.0 (no warnings). `gitConfiguration` is passed for the
development stage only: `gitConfiguration: environmentName == 'development' ? gitConfig : null`
with the object in that stage's parameter file. A customer-managed key adds `managedIdentities:
{ systemAssigned: true, userAssignedResourceIds: [identityId] }` and `customerManagedKey:
{ keyVaultResourceId, keyName, userAssignedIdentityResourceId: identityId, autoRotationEnabled: true }`.

### The runtime key and the source roles

`create_key_only` adds `{ name: 'shir-onprem', type: 'SelfHosted' }` to `integrationRuntimes`; the
key is `listAuthKeys('<runtime id>', '2018-06-01').authKey1`, written into a Key Vault secret in the
same template and never output. `source_access` is a `roleAssignments` entry on each source's module
with `principalId: adf.outputs.systemAssignedMIPrincipalId` - rendered beside the source. Managed
private endpoint connections are approved on the source by the pipeline where this deployment
owns it.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the managed
network and its endpoints, the runtimes, global parameters, the git object, public access, both
private endpoints' services, the identity, the key, and the diagnostic categories. `source_access`,
the endpoint approvals and the runtime key are `not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.DataFactory/factories`:

| Decision | Property |
|---|---|
| the factory | `identity { type, userAssignedIdentities }`, `properties.publicNetworkAccess`, `properties.repoConfiguration`, `properties.globalParameters`, `properties.encryption { keyName, vaultBaseUrl, identity }`, `properties.purviewConfiguration.purviewResourceId` |
| `managed_virtual_network` | child `managedVirtualNetworks/default` and child `integrationRuntimes` (`type: 'Managed'`, `managedVirtualNetwork.referenceName`) |
| `managed_private_endpoints` | child `managedVirtualNetworks/default/managedPrivateEndpoints` |
| `self_hosted_integration_runtime` | child `integrationRuntimes` (`type: 'SelfHosted'`) |
| private endpoints | `Microsoft.Network/privateEndpoints` with `groupIds: ['dataFactory']` and `['portal']` |
| `role_assignments` | `Microsoft.Authorization/roleAssignments` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` with `logAnalyticsDestinationType: 'Dedicated'`, `logs: [ { category } ]`, `metrics: [ { category: 'AllMetrics' } ]` |
