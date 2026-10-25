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

| Decision | Parameter | Note |
|---|---|---|
| `zone_names` | `name` | One module call per zone, in a `[for zone in zoneNames: ...]` loop |
| (global resource) | `location: 'global'` | The module's default is `'global'` as well; written anyway |
| `vnet_links` | `virtualNetworkLinks: [ { name, virtualNetworkResourceId, registrationEnabled, resolutionPolicy } ]` | `name` is `pdnsz-<role>` |
| `auto_registration` | `virtualNetworkLinks[].registrationEnabled` | |
| `resolution_policy` | `virtualNetworkLinks[].resolutionPolicy` | `'Default'` or `'NxDomainRedirect'` |
| `static_records` | `a`, `aaaa`, `cname`, `txt` ... | An array per type: `a: [ { name, ttl, aRecords: [ { ipv4Address } ] } ]`, `cname: [ { name, ttl, cnameRecord: { cname } } ]`, `txt: [ { name, ttl, txtRecords: [ { value: [ ... ] } ] } ]` |
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
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the zone name,
the link count, `registrationEnabled` and `resolutionPolicy` per link, the record arrays.

## Authored rendering

The fallback. `Microsoft.Network/privateDnsZones` (`location: 'global'`) with the child
`Microsoft.Network/privateDnsZones/virtualNetworkLinks` (`properties.virtualNetwork.id`,
`registrationEnabled`, `resolutionPolicy`; also `location: 'global'`) and the record children
(`.../A`, `.../CNAME`, `.../TXT`). Validated with `bicep build`.
