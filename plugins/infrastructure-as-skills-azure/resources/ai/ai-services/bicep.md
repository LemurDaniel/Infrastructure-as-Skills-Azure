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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| (derived from the name) | `customSubDomainName` | **Required** with `networkAcls` or `privateEndpoints`; written |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
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

    // decision: ai-services.identity.managed_identity - none; `{ systemAssigned: true }` once it reaches storage or search
    managedIdentities: {}
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
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); `allowed_fqdns`
is asserted on the second deployment or `not_testable` when empty.

## Authored rendering

The fallback. `Microsoft.CognitiveServices/accounts` with `kind`, `sku`, `identity` and `properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Properties no decision covers

| Input | Property |
|---|---|
| (subdomain) | `properties.customSubDomainName` |
