# Rendering a standalone private endpoint as Bicep

Mapping from the question set to `Microsoft.Network/privateEndpoints`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
A resource whose module carries `privateEndpoints` renders its endpoints there - see
[notes.md](notes.md#when-this-set-is-used-and-when-it-is-not).

```bash
bicep build --stdout modules/private-endpoint.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/private-endpoint:<version>` | **0.12.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| the interface name | `customNetworkInterfaceName` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set.

### The call

```bicep
module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.12.1' = {
  name: 'private-endpoint'
  params: {
    name: privateEndpointName
    location: location
    tags: tags

    // decision: private-endpoint.networking.subnet
    subnetResourceId: subnetResourceId
    customNetworkInterfaceName: '${privateEndpointName}-nic'

    // decision: private-endpoint.target.target_resource
    // decision: private-endpoint.target.subresource - one group id per endpoint
    privateLinkServiceConnections: [
      {
        name: privateEndpointName
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: ['vault']
        }
      }
    ]

    // decision: private-endpoint.dns.dns_zone_group - attached. For left_to_policy leave the
    // parameter out: no zone group is rendered and the platform policy writes the record.
    privateDnsZoneGroup: {
      name: 'default'
      privateDnsZoneGroupConfigs: [for zoneId in privateDnsZoneResourceIds: { privateDnsZoneResourceId: zoneId }]
    }

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = privateEndpoint.outputs.resourceId
output networkInterfaceResourceIds array = privateEndpoint.outputs.networkInterfaceResourceIds
```

Validated with `bicep build` against the published module, including the
`manualPrivateLinkServiceConnections` and `ipConfigurations` forms. With several sub-resources
the module is called in a `[for group in groupIds: ...]` loop, one endpoint each, with the
group id in the deployment name and the endpoint's name.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the group id,
the target, the subnet, the zone group present with the expected zone - or **absent** for
`left_to_policy`, asserted as `privateDnsZoneGroup` not in the parameters.

## Authored rendering

The fallback. `Microsoft.Network/privateEndpoints` with `properties.subnet.id`,
`customNetworkInterfaceName` and `privateLinkServiceConnections` (or
`manualPrivateLinkServiceConnections`); the zone group is the child resource
`Microsoft.Network/privateEndpoints/privateDnsZoneGroups` with `privateDnsZoneConfigs`, declared
only for `dns_zone_group: attached`.
