# Rendering an Azure Relay namespace as Bicep

Mapping from the question set to the namespace. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/relay-namespace.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/relay/namespace:<version>` | **0.8.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The
module deploys the namespace with API version `2021-11-01` and writes `properties: {}` on it:
public access lives in the `networkRuleSets` child, not on the namespace.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Input | Parameter | Note |
|---|---|---|
| tier (no decision) | `skuName: 'Standard'` | The only allowed value; written |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | In the stages the deployment names |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module relayNamespace 'br/public:avm/res/relay/namespace:0.8.0' = {
  name: 'relay-namespace'
  params: {
    name: relayNamespaceName
    location: location
    tags: tags

    // the one tier - no decision, written because the module takes the parameter
    skuName: 'Standard'

    // decision: relay-namespace.access.local_auth - the module would declare the root rule; the template owns none
    authorizationRules: []

    // decision: relay-namespace.connections.hybrid_connections, client_authorization_required
    hybridConnections: [
      {
        name: 'sql-onprem'
        requiresClientAuthorization: true
        userMetadata: '[{"key":"endpoint","value":"db01.corp.example:1433"}]'
      }
    ]
    // decision: relay-namespace.connections.wcf_relays - SAS-only, a named departure per entry
    wcfRelays: wcfRelays

    // decision: relay-namespace.networking.public_network_access, ip_rules - the child rule set carries both
    networkRuleSets: {
      publicNetworkAccess: 'Disabled'
      defaultAction: 'Deny'
      ipRules: []
    }
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'namespace'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'HybridConnectionsEvent' }
          { category: 'VNetAndIPFilteringLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = relayNamespace.outputs.resourceId
```

The `hybridConnections` array is built from the spec's entries. Under `enabled_with_firewall`
the rule set takes `publicNetworkAccess: 'Enabled'` and the allowlist in `ipRules`. A listener's
and a sender's roles (`Azure Relay Listener`, `Azure Relay Sender`) are granted on the
connection by the pattern that owns both sides - `hybridConnections[].roleAssignments` is the
place when the principal is known at render time. A WCF relay entry takes its `Listen` rule in
`wcfRelays[].authorizationRules`, the one SAS case, recorded as a departure.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `skuName`,
`authorizationRules` (asserted empty), the `hybridConnections` array down to
`requiresClientAuthorization`, `networkRuleSets.publicNetworkAccess`, the diagnostic categories.

## Authored rendering

The fallback. `Microsoft.Relay/namespaces@2024-01-01` with `sku` and `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Properties no decision covers

| Input | Property |
|---|---|
| tier | `sku: { name: 'Standard', tier: 'Standard' }` (beside `properties`) |
