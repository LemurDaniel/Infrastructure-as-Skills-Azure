# Rendering a private DNS zone as Bicep

Mapping from the question set to `Microsoft.Network/privateDnsZones`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/private-dns-zone.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/private-dns-zone:<version>` | **0.8.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set. `soa`, `mx`, `srv`, `ptr` and
`roleAssignments` are parameters the question set has no decision for - leave them unset.

### The call

```bicep
module privateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.1' = {
  name: 'private-dns-zone'
  params: {
    name: zoneName
    location: 'global'
    tags: tags

    // decision: private-dns-zone.networking.vnet_links
    virtualNetworkLinks: [
      for (networkId, i) in virtualNetworkIds: {
        name: 'pdnsz-${i}'
        virtualNetworkResourceId: networkId
        // decision: private-dns-zone.networking.auto_registration
        registrationEnabled: false
        // decision: private-dns-zone.networking.resolution_policy
        resolutionPolicy: 'Default'
      }
    ]

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = privateDnsZone.outputs.resourceId
```

For `zone_kind: internal_domain`, `static_records` becomes the record arrays, for example
`a: [ { name: 'app', ttl: 300, aRecords: [ { ipv4Address: '10.0.0.4' } ] } ]`, and
`registrationEnabled` follows `auto_registration`. Validated with `bicep build` against the
published module, records included.

The ids go to the private-endpoint renders (`privateDnsZoneGroup`) and to the resources' own
`privateEndpoints` parameters, by zone name.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the zone name,
the link count, `registrationEnabled` and `resolutionPolicy` per link, the record arrays.

## Authored rendering

The fallback. `Microsoft.Network/privateDnsZones` (`location: 'global'`) with the child
`Microsoft.Network/privateDnsZones/virtualNetworkLinks` (`properties.virtualNetwork.id`,
`registrationEnabled`, `resolutionPolicy`; also `location: 'global'`) and the record children
(`.../A`, `.../CNAME`, `.../TXT`). Validated with `bicep build`.
