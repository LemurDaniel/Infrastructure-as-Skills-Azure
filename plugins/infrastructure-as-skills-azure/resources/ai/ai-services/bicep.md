# Rendering a single-service AI account as Bicep

Mapping from the question set to the account. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
The module is the one of the [Foundry](../foundry/bicep.md) reference; read it first, only what
differs is here.

```bash
bicep build --stdout modules/ai-services.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/cognitive-services/account:<version>` | **0.19.1** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `kind` | `kind` | **Required** |
| `sku_name` | `sku` | Default `'S0'`; written |
| (derived from the name) | `customSubDomainName` | **Required** with `networkAcls` or `privateEndpoints`; written |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Unset, disabled only with private endpoints and no `networkAcls`; written |
| `ip_rules` | `networkAcls: { defaultAction: 'Deny', ipRules: [ { value } ] }` | |
| `restrict_outbound` | `restrictOutboundNetworkAccess` | Default **`true`**; written |
| `allowed_fqdns` | - | **No parameter** in the module. The allowlist is `properties.allowedFqdnList`: render it with a second deployment against the account (an `existing` reference and a `Microsoft.CognitiveServices/accounts` update), and say so in the handover |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'account' } ]` | |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `role_assignments` | `roleAssignments` | The per-kind roles by name |
| `local_authentication_disabled` | `disableLocalAuth` | Default `true`; written |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyName, keyVaultResourceId, userAssignedIdentityResourceId }` | Spelling from the README |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not used here: `deployments`, `allowProjectManagement`, `networkInjections` - Foundry inputs.

### The call

```bicep
module speech 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'speech'
  params: {
    name: speechName
    location: location
    tags: tags
    kind: 'SpeechServices' // decision: ai-services.account.kind
    sku: 'S0' // decision: ai-services.account.sku_name
    customSubDomainName: speechName

    // decision: ai-services.networking.public_network_access, restrict_outbound
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

    managedIdentities: { systemAssigned: true }
    // decision: ai-services.security.local_authentication_disabled
    disableLocalAuth: true
    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'Audit' }
          { category: 'RequestResponse' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = speech.outputs.resourceId
output endpoint string = speech.outputs.endpoint
```

`allowed_fqdns` with entries is the second deployment the Foundry reference shows (an
`existing` account and an update of `properties.allowedFqdnList`).

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); `allowed_fqdns`
is asserted on the second deployment or `not_testable` when empty.

## Authored rendering

The fallback. `Microsoft.CognitiveServices/accounts` with `kind`, `sku`, `identity` and `properties`:

| Decision | Property |
|---|---|
| (subdomain) | `properties.customSubDomainName` |
| `public_network_access`, `ip_rules` | `properties.publicNetworkAccess`, `properties.networkAcls` |
| `restrict_outbound`, `allowed_fqdns` | `properties.restrictOutboundNetworkAccess`, `properties.allowedFqdnList` |
| `local_authentication_disabled` | `properties.disableLocalAuth` |
| `key_management` | `properties.encryption: { keySource: 'Microsoft.KeyVault', keyVaultProperties }` |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: [ 'account' ]` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` scoped to the account |
