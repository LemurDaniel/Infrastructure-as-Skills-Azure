# Rendering a Container Registry as Bicep

Mapping from the question set to the registry. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/container-registry.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/container-registry/registry:<version>` | **0.13.1** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `acrSku` | Default `'Premium'`; written |
| `zone_redundant` | `zoneRedundancy: 'Enabled'` / `'Disabled'` | Default `'Enabled'`; a string here, a bool in Terraform; written |
| `geo_replicas` | `replications: [ { location, zoneRedundancy } ]` | |
| `retention_untagged_days` | `retentionPolicyDays`, `retentionPolicyStatus: 'enabled'` | Default 15 (Terraform 7); written |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Unset, it is disabled only when private endpoints are set |
| `ip_rules` | `networkRuleSetIpRules`, `networkRuleSetDefaultAction: 'Deny'` | Default action `Deny` |
| `network_rule_bypass` | `networkRuleBypassOptions: 'None'` / `'AzureServices'` | Default **`'AzureServices'`** (Terraform: `None`); written |
| `export_policy_enabled` | `exportPolicyStatus: 'enabled'` / `'disabled'` | Default `'disabled'`; written |
| `image_push_path` | nothing on the registry | The image pipeline's steps and the AcrPush assignment for its identity; with `pipeline_opens_registry` the registry's public access is the pipeline's between its steps, so the render keeps `'Disabled'` |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'registry' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `managed_identity` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `role_assignments` | `roleAssignments` | `roleAssignmentMode` left at its default |
| `admin_enabled` | `acrAdminUserEnabled` | Default `false`; written |
| `anonymous_pull_enabled` | `anonymousPullEnabled` | Default `false`; written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, ... }` | Unversioned; the identity member from the README |
| diagnostics | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'container-registry'
  params: {
    name: registryName
    location: location
    tags: tags

    acrSku: 'Premium'
    // decision: container-registry.registry.zone_redundant - fixed at creation
    zoneRedundancy: 'Enabled'
    replications: []
    // decision: container-registry.registry.retention_untagged_days - Terraform's default is 7
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 7

    // decision: container-registry.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: container-registry.networking.network_rule_bypass - the module default is AzureServices
    networkRuleBypassOptions: 'None'
    exportPolicyStatus: 'disabled'
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'registry'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: container-registry.security.admin_enabled
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ContainerRegistryRepositoryEvents' }
          { category: 'ContainerRegistryLoginEvents' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = registry.outputs.resourceId
output loginServer string = registry.outputs.loginServer
```

Output names are read from the README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.ContainerRegistry/registries` with `sku` and `properties`:

| Decision | Property |
|---|---|
| `sku` | `sku.name` |
| `zone_redundant` | `properties.zoneRedundancy` |
| `geo_replicas` | child `replications` |
| `retention_untagged_days` | `properties.policies.retentionPolicy: { days, status }` |
| `public_network_access` | `properties.publicNetworkAccess`, `networkRuleSet` |
| `network_rule_bypass` | `properties.networkRuleBypassOptions` |
| `export_policy_enabled` | `properties.policies.exportPolicy.status` |
| `admin_enabled`, `anonymous_pull_enabled` | `properties.adminUserEnabled`, `properties.anonymousPullEnabled` |
