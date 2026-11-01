# Rendering a route table as Bicep

Mapping from the question set to `Microsoft.Network/routeTables`. General layout, parameters
and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/route-table.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/route-table:<version>` | **0.5.0** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| (the table) | `name` | Assembled from the `rt` abbreviation, affix, workload and subnet role |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set. `lock` and `roleAssignments` are
parameters the question set has no decision for - leave them unset.

### The call

```bicep
module routeTable 'br/public:avm/res/network/route-table:0.5.0' = {
  name: 'route-table'
  params: {
    name: routeTableName
    location: location
    tags: tags

    // decision: route-table.networking.bgp_route_propagation - inverted: disabled is true
    disableBgpRoutePropagation: true

    routes: [
      // decision: route-table.networking.default_route
      {
        name: 'default-to-firewall'
        properties: {
          addressPrefix: '0.0.0.0/0'
          nextHopType: 'VirtualAppliance'
          nextHopIpAddress: firewallPrivateIp // decision: route-table.networking.firewall_private_ip
        }
      }
    ]

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = routeTable.outputs.resourceId
```

Validated with `bicep build` against the published module. The output `resourceId` is what the
virtual-network set takes for a subnet's `routeTableResourceId`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)):
`disableBgpRoutePropagation` is `true`, the default route is present with `VirtualAppliance`
and the firewall's address, every further route has a known next-hop type. The inversion is the
one to assert on purpose - a reader sees `true` and thinks "propagation on".

## Authored rendering

The fallback. `Microsoft.Network/routeTables` with `properties.disableBgpRoutePropagation` and
`properties.routes`, each route with `name` and `properties { addressPrefix, nextHopType,
nextHopIpAddress }`. Routes as child resources (`.../routes`) and routes inline in the table's
properties are alternatives, not a pair: mixing them makes a redeploy remove one or the other.
Validated with `bicep build`.
