# Rendering a public IP address as Bicep

Mapping from the question set to `Microsoft.Network/publicIPAddresses`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/public-ip-address.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/public-ip-address:<version>` | **0.13.0** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module publicIp 'br/public:avm/res/network/public-ip-address:0.13.0' = {
  name: 'public-ip-address'
  params: {
    name: publicIpName
    location: location
    tags: tags

    // decision: public-ip-address.address.sku
    skuName: 'Standard'
    // decision: public-ip-address.address.sku_tier
    skuTier: 'Regional'
    // decision: public-ip-address.address.allocation_method
    publicIPAllocationMethod: 'Static'
    // decision: public-ip-address.address.ip_version
    publicIPAddressVersion: 'IPv4'
    // decision: public-ip-address.address.zones
    availabilityZones: [1, 2, 3]
    // decision: public-ip-address.address.idle_timeout_minutes
    idleTimeoutInMinutes: 4

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        // decision: public-ip-address.observability.diagnostic_categories
        logCategoriesAndGroups: [
          { category: 'DDoSProtectionNotifications' }
          { category: 'DDoSMitigationFlowLogs' }
          { category: 'DDoSMitigationReports' }
        ]
        // decision: public-ip-address.observability.metrics_enabled
        metricCategories: [
          { category: 'AllMetrics' }
        ]
      }
    ]
    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = publicIp.outputs.resourceId
output ipAddress string = publicIp.outputs.ipAddress
```

Validated with `bicep build` against the published module. `ipAddress` is empty at the end of
the deployment for an address that is not yet allocated; a Static one has it.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml except the two DDoS rows is observable in
`tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `skuName`,
`skuTier`, `publicIPAllocationMethod`, `publicIPAddressVersion`, `availabilityZones`,
`idleTimeoutInMinutes`, and the diagnostic categories. `ddos_protection_mode: VirtualNetworkInherited`
is the **absence** of `ddosSettings` and is asserted as that.

## Authored rendering

The fallback. `Microsoft.Network/publicIPAddresses` with `sku: { name, tier }`, `zones` (strings),
and `properties.publicIPAllocationMethod`, `publicIPAddressVersion`, `idleTimeoutInMinutes`,
`dnsSettings.domainNameLabel` and `ddosSettings.protectionMode`, which authored takes
`VirtualNetworkInherited` and `Disabled` as well. Diagnostics are a
`Microsoft.Insights/diagnosticSettings` extension resource with `scope: publicIp`.
