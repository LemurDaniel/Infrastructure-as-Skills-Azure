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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoints | |
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
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the managed
group name, the Event Hubs state, both public-access strings, each endpoint array, the identity
and the diagnostic categories. `collection_roles` and the `existing` reference under
`ownership: platform` are `not-testable` (not a resource of this template).

## Authored rendering

The fallback. `Microsoft.Purview/accounts@2021-12-01`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Input | Property |
|---|---|
| `deployment.resource_lock` | `Microsoft.Authorization/locks` (`CanNotDelete`) |
