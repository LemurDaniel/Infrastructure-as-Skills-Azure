# Rendering an AI Foundry account as Bicep

Mapping from the question set to the account. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/foundry.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/cognitive-services/account:<version>` | **0.19.1** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The
module's own `deployment` and `project` child modules are `Proposed` in the index; the
`deployments` parameter of the account module is the supported route.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `kind` | `kind` | **Required** |
| `sku_name` | `sku` | Default `'S0'`; written |
| (derived from the name) | `customSubDomainName` | **Required** with `networkAcls` or `privateEndpoints`; written |
| `project_management` | `allowProjectManagement` | No default; written |
| `projects` | **not the module** - child resources below | |
| `model_deployments`, `deployment_sku`, `deployment_capacity`, `version_upgrade_option`, `content_filter` | `deployments: [ { name, model: { format, name, version }, sku: { name, capacity }, versionUpgradeOption, raiPolicyName } ]` | `sku.name` carries the deployment type |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Unset, it is disabled only when private endpoints are set and no `networkAcls`; written |
| `ip_rules` | `networkAcls: { defaultAction: 'Deny', ipRules: [ { value } ] }` | |
| `restrict_outbound` | `restrictOutboundNetworkAccess` | Default **`true`**; written |
| `allowed_fqdns` | - | **No parameter** in the module. The allowlist is `properties.allowedFqdnList` on the account: render it with a second deployment against the account (an `existing` reference and a `Microsoft.CognitiveServices/accounts` update), and say so in the handover |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'account' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `managed_identity` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `role_assignments` | `roleAssignments` | |
| `local_authentication_disabled` | `disableLocalAuth` | Default `true`; written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, ... }` - spelling from the README | |
| diagnostics | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryName
    location: location
    tags: tags

    kind: 'AIServices'
    sku: 'S0'
    customSubDomainName: foundryName
    allowProjectManagement: true

    // decision: foundry.models.* - one entry per deployment; the model and version are pinned
    deployments: [
      {
        name: 'chat'
        // name, version and format from the spec's model_deployments, chosen from models.yaml
        model: { format: '<format>', name: '<model>', version: '<version>' }
        sku: { name: 'DataZoneStandard', capacity: 10 }
        versionUpgradeOption: 'OnceCurrentVersionExpired'
        raiPolicyName: 'Microsoft.DefaultV2'
      }
    ]

    // decision: foundry.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    restrictOutboundNetworkAccess: true
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'account'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: foundry.identity.managed_identity - none; `{ systemAssigned: true }` once it reaches storage or search
    managedIdentities: {}
    // decision: foundry.security.local_authentication_disabled
    disableLocalAuth: true
    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'Audit' }
          { category: 'RequestResponse' }
          { category: 'AzureOpenAIRequestUsage' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = foundry.outputs.resourceId
output endpoint string = foundry.outputs.endpoint
```

The model name and version are an example of the shape; the real ones are looked up against
the region's catalogue. Parameter and output spellings (`customerManagedKey`, `endpoint`)
are read from the README of the pinned version.

### Another region

When the spec carries `resources.<key>.placement.location`, the account takes its own
parameter, one value in every stage file. The module puts the private endpoint into its
virtual network's region when the entry names none; the render writes it anyway, so the call
says where each part runs. The names do not change - the account's pattern carries no region.

```bicep
// decision: foundry.placement.location - departs from location for the model catalogue
@description('Region of the Foundry account, apart from location.')
param foundryLocation string

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  params: {
    location: foundryLocation
    privateEndpoints: [
      {
        name: privateEndpointName
        location: location // the subnet's region, never the account's
        service: 'account'
        subnetResourceId: privateEndpointSubnetId
      }
    ]
    // ...
  }
}
```

The projects take `foundryLocation` too. The ARM test asserts the account on
`foundryLocation` and the endpoint on `location`.

### Projects

Not in the module; a child resource next to it, with its own identity:

```bicep
resource accountRef 'Microsoft.CognitiveServices/accounts@<api-version>' existing = {
  name: foundryName
  dependsOn: [ foundry ]
}

resource project 'Microsoft.CognitiveServices/accounts/projects@<api-version>' = [for p in projects: {
  parent: accountRef
  name: p
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
}]
```

The API version is the compiled module's, not recalled.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above, deployments included, is observable in
`tests/*.armtest.yaml` ([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.CognitiveServices/accounts` with `kind`, `sku` and `properties`:

| Decision | Property |
|---|---|
| `project_management` | `properties.allowProjectManagement` |
| `public_network_access`, `ip_rules` | `properties.publicNetworkAccess`, `properties.networkAcls` |
| `restrict_outbound` | `properties.restrictOutboundNetworkAccess` |
| `allowed_fqdns` | `properties.allowedFqdnList` |
| `local_authentication_disabled` | `properties.disableLocalAuth` |
| deployments | child `accounts/deployments` with `sku` and `properties.model`, `versionUpgradeOption`, `raiPolicyName` - created one after another (`@batchSize(1)`) |
| `projects` | child `accounts/projects` |
