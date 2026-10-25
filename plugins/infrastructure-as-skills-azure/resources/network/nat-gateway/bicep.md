# Rendering a NAT gateway as Bicep

Mapping from the question set to `Microsoft.Network/natGateways`. General layout, parameters
and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/nat-gateway.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/nat-gateway:<version>` | **2.1.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module is
at a major version of 2, unlike most; a repository on 1.x re-reads its parameters.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `natGatewaySku` | **Module default is `Standard`**, the Terraform module's `StandardV2`: written on every call |
| `zone` | `availabilityZone` | **Required.** `1`, `2` or `3` for a `Standard` gateway; `-1` for `none`, and for `StandardV2`, which ignores it |
| `public_ip_source: with_gateway`, `public_ip_count` | `publicIPAddresses: [ { name, skuName, publicIPAllocationMethod: 'Static', availabilityZones } ]` | One entry per address, 1 to 16; `skuName` equal to `natGatewaySku` |
| `public_ip_source: separate` | `publicIpResourceIds` | The ids from the `public-ip-address` set (`purpose: nat_gateway`) |
| `public_ip_prefix_ids` | `publicIPPrefixResourceIds` | IPv4; the IPv6 variants are not used |
| `idle_timeout_minutes` | `idleTimeoutInMinutes` | |
| `subnets` | not a parameter here | The association is the virtual-network set's `subnets[].natGatewayResourceId: natGateway.outputs.resourceId` |
| `diagnostic_workspace`, `metrics_enabled` | **not carried** | The module has no `diagnosticSettings` for the gateway (only for the addresses it creates) - see below |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

**Not carried by the module at 2.1.1:** the gateway's own diagnostic setting
(`nat-gateway.observability.diagnostic_workspace`, `metrics_enabled`). The decision stays in the
spec; the render adds `Microsoft.Insights/diagnosticSettings` as an extension resource with
`scope` set to the gateway (authored, below). The addresses the module creates take
`publicIPAddresses[].diagnosticSettings` for their DDoS categories, as in the `public-ip-address`
set; that is a decision of that set, not this one.

### The call

```bicep
module natGateway 'br/public:avm/res/network/nat-gateway:2.1.1' = {
  name: 'nat-gateway'
  params: {
    name: natGatewayName
    location: location
    tags: tags

    // decision: nat-gateway.gateway.sku
    natGatewaySku: 'StandardV2'
    // decision: nat-gateway.gateway.zone - required parameter; -1 is no zone, and StandardV2 ignores it
    availabilityZone: -1
    // decision: nat-gateway.gateway.idle_timeout_minutes
    idleTimeoutInMinutes: 4

    // decision: nat-gateway.gateway.public_ip_source - with_gateway
    // decision: nat-gateway.gateway.public_ip_count - one entry per name
    publicIPAddresses: [
      for ipName in publicIpNames: {
        name: ipName
        skuName: 'StandardV2' // must match natGatewaySku
        publicIPAllocationMethod: 'Static'
        availabilityZones: [1, 2, 3]
      }
    ]
    // decision: nat-gateway.gateway.public_ip_prefix_ids
    publicIPPrefixResourceIds: publicIpPrefixResourceIds

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = natGateway.outputs.resourceId
```

For `sku: Standard`: `natGatewaySku: 'Standard'`, `availabilityZone: 1` (or `-1`), `skuName:
'Standard'` and `availabilityZones: [1]` on the addresses. Validated with `bicep build` against
the published module, both generations and the `publicIpResourceIds` form.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above except the diagnostic setting is observable in
`tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `natGatewaySku`,
`availabilityZone`, `idleTimeoutInMinutes`, the address count and each address's `skuName`
matching the gateway's, and `publicIPPrefixResourceIds` empty. The diagnostic setting, rendered
authored beside the module, is asserted on that resource.

## Authored rendering

The fallback - and the render of the diagnostic setting, which the module does not carry.
`Microsoft.Network/natGateways` with `sku.name`, `zones` (strings, for `Standard`),
`properties.idleTimeoutInMinutes` and `properties.publicIpAddresses[].id` (and
`publicIpPrefixes[].id`); the addresses are `Microsoft.Network/publicIPAddresses` as in the
`public-ip-address` set. The subnet takes the gateway through `properties.natGateway.id`.
Diagnostics: `Microsoft.Insights/diagnosticSettings` with `scope: natGateway` and
`metrics: [ { category: 'AllMetrics', enabled: true } ]`. Validated with `bicep build`.
