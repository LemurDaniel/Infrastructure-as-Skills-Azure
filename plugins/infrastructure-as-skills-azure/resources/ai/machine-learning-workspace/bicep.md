# Rendering an Azure Machine Learning workspace as Bicep

Mapping from the question set to the workspace. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/machine-learning-workspace.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/machine-learning-services/workspace:<version>` | **0.14.1** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
carries `computes`, `connections` and `datastores` as nested parameters.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| (kind) | `kind: 'Default'` | Default `'Default'`; written |
| (edition) | `sku: 'Basic'` | **Required** by the module; the only edition in use |
| `storage_account`, `key_vault`, `application_insights` | `associatedStorageAccountResourceId`, `associatedKeyVaultResourceId`, `associatedApplicationInsightsResourceId` | Required for `Default`; a missing key vault makes the service create a Microsoft-managed one |
| `container_registry` | `associatedContainerRegistryResourceId` | Omitted when empty |
| `hbi_workspace` | `hbiWorkspace` | Default `false`; written |
| `v1_legacy_mode` | - | **Not carried by the module** (`properties.v1LegacyMode`); a second deployment against the workspace when `true`; off is the platform default |
| `image_build_compute` | `imageBuildCompute` | |
| `computes` | `computes: [ { name, computeType, location, sku, properties } ]` | Names only from the set; the sizing is content |
| `managed_network_isolation` | `managedNetworkSettings: { isolationMode }` | Unset by default; written |
| `outbound_fqdns` | `managedNetworkSettings.outboundRules: { <name>: { type: 'FQDN', destination, category: 'UserDefined' } }` | The rule name is the object key; `firewallSku` beside it |
| `provision_network_now` | `provisionNetworkNow` | Unset by default; written |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Module default `'Disabled'`; written |
| `ip_allowlist` | `ipAllowlist` | |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'amlworkspace' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `serverless_compute_no_public_ip` | `serverlessComputeSettings: { serverlessComputeNoPublicIP }` | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }`, `primaryUserAssignedIdentity` | Module default `{ systemAssigned: true }`; the primary is required with user-assigned and may not be set with system-assigned |
| `role_assignments` | `roleAssignments` | |
| `storage_datastore_auth` | `systemDatastoresAuthMode: 'Identity'` / `'AccessKey'` | Unset by default (key); written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | |
| `service_side_cmk` | `enableServiceSideCMKEncryption` | Unset by default; written |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module mlWorkspace 'br/public:avm/res/machine-learning-services/workspace:0.14.1' = {
  name: 'ml-workspace'
  params: {
    name: mlWorkspaceName
    location: location
    tags: tags
    kind: 'Default'
    sku: 'Basic'

    // decision: machine-learning-workspace.workspace.storage_account, key_vault, application_insights, container_registry
    associatedStorageAccountResourceId: storageAccountId
    associatedKeyVaultResourceId: keyVaultId
    associatedApplicationInsightsResourceId: applicationInsightsId
    associatedContainerRegistryResourceId: containerRegistryId

    hbiWorkspace: false // decision: machine-learning-workspace.workspace.hbi_workspace
    imageBuildCompute: '' // decision: machine-learning-workspace.workspace.image_build_compute
    computes: [] // decision: machine-learning-workspace.workspace.computes

    // decision: machine-learning-workspace.networking.managed_network_isolation, outbound_fqdns
    managedNetworkSettings: {
      isolationMode: 'AllowOnlyApprovedOutbound'
      outboundRules: {}
    }
    provisionNetworkNow: true // decision: machine-learning-workspace.networking.provision_network_now
    // decision: machine-learning-workspace.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    ipAllowlist: []
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'amlworkspace'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the records
      }
    ]
    serverlessComputeSettings: {
      serverlessComputeNoPublicIP: true // decision: machine-learning-workspace.networking.serverless_compute_no_public_ip
    }

    managedIdentities: { systemAssigned: true }
    // decision: machine-learning-workspace.security.storage_datastore_auth, service_side_cmk
    systemDatastoresAuthMode: 'Identity'
    enableServiceSideCMKEncryption: false
    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'AmlComputeClusterEvent' }
          { category: 'AmlComputeJobEvent' }
          { category: 'AmlRunStatusChangedEvent' }
          { category: 'ModelsChangeEvent' }
          { category: 'DataStoreChangeEvent' }
          { category: 'ManagedNetworkEvent' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = mlWorkspace.outputs.resourceId
```

An FQDN rule is `outboundRules: { pypi: { type: 'FQDN', destination: 'pypi.org', category: 'UserDefined' } }`;
the member names of a rule are read from the README of the pinned version. `v1_legacy_mode: true`
is a second deployment against the workspace (an `existing` reference and an update of
`properties.v1LegacyMode`), said so in the handover.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); `v1_legacy_mode`
at its default is `not_testable` (rendered nowhere).

## Authored rendering

The fallback. `Microsoft.MachineLearningServices/workspaces` with `kind`, `sku`, `identity` and
`properties`:

| Decision | Property |
|---|---|
| dependencies | `properties.storageAccount`, `keyVault`, `applicationInsights`, `containerRegistry` |
| `hbi_workspace`, `v1_legacy_mode`, `image_build_compute` | `properties.hbiWorkspace`, `v1LegacyMode`, `imageBuildCompute` |
| `managed_network_isolation`, `outbound_fqdns`, `provision_network_now` | `properties.managedNetwork: { isolationMode, outboundRules }`, `provisionNetworkNow` |
| `public_network_access`, `ip_allowlist` | `properties.publicNetworkAccess`, `ipAllowlist` |
| `serverless_compute_no_public_ip` | `properties.serverlessComputeSettings.serverlessComputeNoPublicIP` |
| `managed_identity` | `identity` (top level), `properties.primaryUserAssignedIdentity` |
| `storage_datastore_auth` | `properties.systemDatastoresAuthMode` |
| `key_management`, `service_side_cmk` | `properties.encryption`, `enableServiceSideCMKEncryption` |
| `computes` | child `workspaces/computes` |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: [ 'amlworkspace' ]` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` scoped to the workspace |
