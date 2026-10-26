# Rendering a Microsoft Purview account as Bicep

Mapping from the question set to the account. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/purview-account.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/purview/account:<version>` | **0.10.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
builds the account with its managed resources, one private endpoint array per kind (`account`,
`portal`, `blob`, `queue`, `namespace` - the service is fixed per parameter), role assignments, the
lock and the diagnostic setting. `ownership: platform` renders an `existing` reference and no call.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `ownership`, `existing_account_id` | `resource pview 'Microsoft.Purview/accounts@2021-12-01' existing` by id | `platform`: the reference only |
| `managed_resource_group_name` | `managedResourceGroupName` | Module default `managed-rg-<name>`; written. Fixed at creation |
| `managed_event_hub` | `managedEventHubState: 'Disabled' / 'Enabled'` | Module default **`Enabled`**; written |
| `managed_resources_public_access` | `managedResourcesPublicNetworkAccess: 'Disabled' / 'Enabled'` | Module default `NotSpecified`; written |
| `public_network_access` | `publicNetworkAccess: 'Disabled' / 'Enabled'` | Module default `NotSpecified`; written |
| `private_endpoint_subnet`, `private_endpoint_subresources` | `accountPrivateEndpoints`, `portalPrivateEndpoints`, `storageBlobPrivateEndpoints`, `storageQueuePrivateEndpoints`, `eventHubPrivateEndpoints`: each `[ { name, subnetResourceId } ]` | The module targets the managed resources itself; an empty array for a kind that is off |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoints | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | The module sets `SystemAssigned` always and adds `UserAssigned` when ids are passed |
| `collection_roles` | **not the module** - the metadata policy API after the deployment | |
| `role_assignments` | `roleAssignments` | Control plane |
| `diagnostic_workspace`, `diagnostic_categories`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module pview 'br/public:avm/res/purview/account:0.10.0' = {
  name: 'purview-account'
  params: {
    name: pviewName
    location: location
    tags: tags

    // decision: purview-account.account.managed_resource_group_name - the service default
    managedResourceGroupName: 'managed-rg-${pviewName}'
    // decision: purview-account.account.managed_event_hub - the module default is Enabled
    managedEventHubState: 'Disabled'
    // decision: purview-account.account.managed_resources_public_access
    managedResourcesPublicNetworkAccess: 'Disabled'

    // decision: purview-account.networking.public_network_access - the module default is NotSpecified
    publicNetworkAccess: 'Disabled'
    // decision: purview-account.networking.private_endpoint_subnet / private_endpoint_subresources
    accountPrivateEndpoints: [
      {
        name: 'pep-${pviewName}-account'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]
    portalPrivateEndpoints: [
      { name: 'pep-${pviewName}-portal', subnetResourceId: privateEndpointSubnetId }
    ]
    storageBlobPrivateEndpoints: [
      { name: 'pep-${pviewName}-blob', subnetResourceId: privateEndpointSubnetId }
    ]
    storageQueuePrivateEndpoints: [
      { name: 'pep-${pviewName}-queue', subnetResourceId: privateEndpointSubnetId }
    ]
    // namespace: none - managed_event_hub is off
    eventHubPrivateEndpoints: []

    // decision: purview-account.identity.managed_identity - system-assigned is implicit in the module
    managedIdentities: { userAssignedResourceIds: [] }

    // decision: purview-account.observability.diagnostic_workspace / diagnostic_categories / metrics_enabled
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ScanStatusLogEvent' }
          { category: 'DataSensitivityLogEvent' }
          { category: 'Security' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]

    // decision: purview-account.identity.role_assignments
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = pview.outputs.resourceId
output name string = pview.outputs.name
output managedStorageAccountId string = pview.outputs.managedStorageAccountId
```

Validated with `bicep build` against 0.10.0 (no warnings). With `managed_event_hub: true`,
`managedEventHubState: 'Enabled'` and `eventHubPrivateEndpoints: [ { name, subnetResourceId } ]`; a
user-assigned identity goes into `managedIdentities.userAssignedResourceIds`.

### Collection roles

Granted against the account's metadata policy API (`PUT /policystore/metadataPolicies/{id}`,
API version `2021-07-01`) by a deployment script or the pipeline after the deployment, as a
Collection admin - the deploying principal is one by creation. The spec records `collection_roles`
as that step.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the managed
group name, the Event Hubs state, both public-access strings, each endpoint array, the identity
and the diagnostic categories. `collection_roles` and the `existing` reference under
`ownership: platform` are `not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.Purview/accounts@2021-12-01`:

| Decision | Property |
|---|---|
| the account | `identity { type: 'SystemAssigned' | 'SystemAssigned,UserAssigned', userAssignedIdentities }`, `properties.managedResourceGroupName`, `properties.managedEventHubState`, `properties.publicNetworkAccess`, `properties.managedResourcesPublicNetworkAccess` |
| private endpoints | `Microsoft.Network/privateEndpoints` with `groupIds: ['account']` and `['portal']` on the account, `['blob']` and `['queue']` on `properties.managedResources.storageAccount`, `['namespace']` on `properties.managedResources.eventHubNamespace` |
| `role_assignments` | `Microsoft.Authorization/roleAssignments` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` with `logs: [ { category } ]` and `metrics: [ { category: 'AllMetrics' } ]` |
| lock | `Microsoft.Authorization/locks` (`CanNotDelete`) |
