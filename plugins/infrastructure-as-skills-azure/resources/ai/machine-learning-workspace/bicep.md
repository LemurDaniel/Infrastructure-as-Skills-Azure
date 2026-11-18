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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| (kind) | `kind: 'Default'` | Default `'Default'`; written |
| (edition) | `sku: 'Basic'` | **Required** by the module; the only edition in use |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
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
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); `v1_legacy_mode`
at its default is `not_testable` (rendered nowhere).

## Authored rendering

The fallback. `Microsoft.MachineLearningServices/workspaces` with `kind`, `sku`, `identity` and
`properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
