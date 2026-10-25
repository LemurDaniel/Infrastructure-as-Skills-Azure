# Rendering a virtual network peering as Bicep

Mapping from the question set to the peering. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/virtual-network-peering.bicep
```

## With the AVM module

`br/public:avm/res/network/virtual-network/virtual-network-peering:<version>` - the child module of the
virtual network module, and the primary rendering. Documented against **0.2.0** (resolved 2026-10-25);
resolve the current version and re-read its README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. Status: Available (a
child of `avm/res/network/virtual-network`).

**One call creates one direction.** The module has no reverse-peering parameter: the hub side is a
**second call, scoped to the remote network's resource group** with `localVnetName` set to the remote
network and `remoteVirtualNetworkResourceId` to the local one. The subscription, group and name come
out of the remote network's id (`split(id, '/')[2]`, `[4]`, `[8]`); a network in another subscription
works because `scope: resourceGroup(subscriptionId, name)` reaches it and the deployment identity holds
the rights there. The network module also takes a `peerings` array for the local half (see
[the network set](../virtual-network/bicep.md)); use one or the other for a given pair.

**The modules disagree on defaults:** the Bicep module defaults `allowForwardedTraffic` to `true`
(Terraform `false`) and `doNotVerifyRemoteGateways` to `true` (Terraform `false`: the check on). Both
are written in every call.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `local_virtual_network` | `localVnetName` (and the module's scope) | The name of the parent network; the call is scoped to its group |
| `remote_virtual_network` | `remoteVirtualNetworkResourceId` | The hub's id |
| `both_directions` | a second module call scoped to the remote network | `false`: no second call |
| `allow_virtual_network_access` | `allowVirtualNetworkAccess` | |
| `reverse_allow_virtual_network_access` | `allowVirtualNetworkAccess` on the second call | |
| `allow_forwarded_traffic` | `allowForwardedTraffic` | Module default `true` - written |
| `reverse_allow_forwarded_traffic` | `allowForwardedTraffic` on the second call | |
| `allow_gateway_transit` | `allowGatewayTransit` | Hub side only |
| `use_remote_gateways` | `useRemoteGateways` | Spoke side only |
| `reverse_allow_gateway_transit` | `allowGatewayTransit` on the second call | |
| `verify_remote_gateways` | `doNotVerifyRemoteGateways` | Inverted; module default `true` (no check) - written `false` |
| names | `name` | Assembled from vars per side; the module default is `peer-<local>-<remote>` |
| `deployment.module_telemetry` | `enableTelemetry` | |

### The call

```bicep
var remoteSubscriptionId = split(remoteVirtualNetworkId, '/')[2]
var remoteResourceGroupName = split(remoteVirtualNetworkId, '/')[4]
var remoteVirtualNetworkName = split(remoteVirtualNetworkId, '/')[8]

module localPeering 'br/public:avm/res/network/virtual-network/virtual-network-peering:0.2.0' = {
  name: 'peering-local'
  params: {
    name: peeringName
    localVnetName: localVirtualNetworkName
    remoteVirtualNetworkResourceId: remoteVirtualNetworkId

    // decision: virtual-network-peering.peering.allow_virtual_network_access
    allowVirtualNetworkAccess: true
    // decision: virtual-network-peering.networking.allow_forwarded_traffic
    allowForwardedTraffic: true
    // decision: virtual-network-peering.networking.allow_gateway_transit
    allowGatewayTransit: false
    // decision: virtual-network-peering.networking.use_remote_gateways
    useRemoteGateways: false
    // decision: virtual-network-peering.networking.verify_remote_gateways - the module defaults to true (do not verify)
    doNotVerifyRemoteGateways: false
    enableTelemetry: true
  }
}

// decision: virtual-network-peering.peering.both_directions
module reversePeering 'br/public:avm/res/network/virtual-network/virtual-network-peering:0.2.0' = {
  name: 'peering-reverse'
  scope: resourceGroup(remoteSubscriptionId, remoteResourceGroupName)
  params: {
    name: reversePeeringName
    localVnetName: remoteVirtualNetworkName
    remoteVirtualNetworkResourceId: localVirtualNetworkId

    // decision: virtual-network-peering.peering.reverse_allow_virtual_network_access
    allowVirtualNetworkAccess: true
    // decision: virtual-network-peering.networking.reverse_allow_forwarded_traffic
    allowForwardedTraffic: true
    // decision: virtual-network-peering.networking.reverse_allow_gateway_transit
    allowGatewayTransit: false
    useRemoteGateways: false
    doNotVerifyRemoteGateways: false
    enableTelemetry: true
  }
}

output peeringId string = localPeering.outputs.resourceId
output reversePeeringId string = reversePeering.outputs.resourceId
```

The values shown are a spoke behind a hub with a firewall and no gateway. With `hub_gateway: true` and
`peering_role: spoke` the first call has `useRemoteGateways: true` and the second
`allowGatewayTransit: true`, and the second call must exist (and finish) before the first: add
`dependsOn: [ reversePeering ]` to the local call. With `both_directions: false` the second call and
its output are dropped.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the two calls are two
nested deployments, the second with its own `resourceGroup` scope.

## Authored rendering

The fallback. `Microsoft.Network/virtualNetworks/virtualNetworkPeerings`, a child resource of the
network (`parent:` or a nested resource), once per direction:

| Decision | Property |
|---|---|
| `remote_virtual_network` | `properties.remoteVirtualNetwork: { id }` |
| `allow_virtual_network_access`, `allow_forwarded_traffic`, `allow_gateway_transit`, `use_remote_gateways` | `properties.allowVirtualNetworkAccess`, `.allowForwardedTraffic`, `.allowGatewayTransit`, `.useRemoteGateways` |
| `verify_remote_gateways` | `properties.doNotVerifyRemoteGateways` (inverted) |
| `both_directions` | a second resource, declared `existing` for the remote network in `resourceGroup(subscriptionId, name)` through a module scoped to it |
