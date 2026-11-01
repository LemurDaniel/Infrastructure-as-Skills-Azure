# Rendering a virtual network as Bicep

Mapping from the question set to `Microsoft.Network/virtualNetworks`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/network.bicep
```

## With the AVM module

`br/public:avm/res/network/virtual-network:<version>` — the primary rendering for
`network_ownership: create`. Documented against **0.10.2** (resolved 2026-10-17); resolve
the current version and re-read its README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. A referenced network stays
an `existing` reference as below.

### Decision → module parameter

| Decision | Parameter | Note |
|---|---|---|
| `address_space` | `addressPrefixes: [addressSpace]` | |
| `dns_servers` | `dnsServers` | Omit for Azure DNS |
| `ddos_protection` | `ddosProtectionPlanResourceId` | |
| `subnets` | `subnets: [ { name, addressPrefix, … } ]` | The module declares them inline on the vnet — the safe form, as the authored render says — and still outputs `subnetResourceIds` |
| `private_endpoint_network_policies` | `subnets[].privateEndpointNetworkPolicies: 'Enabled'` | |
| `service_endpoints` | `subnets[].serviceEndpoints: ['Microsoft.Storage']` | Strings, not `{ service }` objects |
| `subnet_delegations` | `subnets[].delegation: 'Microsoft.Web/serverFarms'` | A single string per subnet |
| diagnostics (from the deployment set) | `diagnosticSettings: [ { workspaceResourceId, metricCategories } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

`peerings` is an input too — the spoke-to-hub peering of a `landing_zone: corp` network,
supplied by a pattern skill.

### The call

```bicep
module virtualNetwork 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: virtualNetworkName
    location: location
    tags: tags

    // decision: virtual-network.addressing.address_space
    addressPrefixes: [addressSpace]

    subnets: [
      for subnet in subnets: {
        name: subnet.name
        addressPrefix: subnet.prefix
        // NSG and routes apply to private endpoint traffic.
        privateEndpointNetworkPolicies: 'Enabled'
        serviceEndpoints: subnet.?serviceEndpoints ?? []
      }
    ]

    enableTelemetry: true
  }
}

output id string = virtualNetwork.outputs.resourceId
output subnetResourceIds array = virtualNetwork.outputs.subnetResourceIds
```

`subnetResourceIds` is an array in the order of `subnets`, like the authored render's
loop output — index by position only where the list is fixed, otherwise look the subnet
up as an `existing` child by name.

## Authored rendering

The fallback — `implementation: authored`, a repository that already renders the network
this way, or reading what the module does inside.

## Decision → property

| Decision | Property |
|---|---|
| `address_space` | `properties.addressSpace.addressPrefixes` (array) |
| `dns_servers` | `properties.dhcpOptions.dnsServers` — omit for Azure DNS |
| `ddos_protection` | `properties.enableDdosProtection` + `properties.ddosProtectionPlan.id` |
| `subnets` | `properties.subnets[]`, inline — see below |
| `private_endpoint_network_policies` | `properties.subnets[].properties.privateEndpointNetworkPolicies` |
| `service_endpoints` | `properties.subnets[].properties.serviceEndpoints[].service` |
| `subnet_delegations` | `properties.subnets[].properties.delegations[].properties.serviceName` |

## Inline subnets, unlike Terraform

This is the one place the two targets should **not** look alike. In Bicep, declaring
subnets inline is the safe form:

```bicep
var affix = '${locationAbbreviations[location]}${environmentAbbreviations[environment]}'

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-${affix}-${workload}-01'
  location: location
  tags: tags

  properties: {
    addressSpace: {
      addressPrefixes: [addressSpace]
    }

    subnets: [
      for subnet in subnets: {
        name: subnet.name
        properties: {
          addressPrefix: subnet.prefix
          // NSG and routes apply to private endpoint traffic.
          privateEndpointNetworkPolicies: 'Enabled'
          serviceEndpoints: [for s in subnet.?serviceEndpoints ?? []: { service: s }]
        }
      }
    ]
  }
}
```

A child `Microsoft.Network/virtualNetworks/subnets` resource is also valid, but mixing it
with an inline `subnets` array in one deployment means the vnet's own PUT rewrites the
subnet list and removes whatever the child resource added. If separate child resources are
needed — because another module owns a subnet — then the vnet must declare **no** inline
subnets at all.

## Referencing a subnet from another module

```bicep
output subnetIds object = reduce(
  virtualNetwork.properties.subnets,
  {},
  (acc, s) => union(acc, { '${s.name}': s.id })
)
```

Or, simpler and usually enough, an output per subnet that consumers actually need:

```bicep
output privateEndpointSubnetId string = virtualNetwork.properties.subnets[0].id
```

Indexing by position is brittle the moment the list changes — prefer
`filter(virtualNetwork.properties.subnets, s => s.name == privateEndpointSubnetName)[0].id`
or pass the name in and look it up as an `existing` child resource.

## Diagnostics

Attached to the network, not to a subnet — a subnet has no diagnostic surface of its own.
Flow logs are a Network Watcher resource in the region, not a property here, and the
Network Watcher itself is usually platform-owned and already present.
