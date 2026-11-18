# Rendering an Azure Firewall as Bicep

Mapping from the question set to the firewall, its policy and its public addresses. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/azure-firewall.bicep
```

## With the AVM modules

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/azure-firewall:<version>` | **0.11.1** | 2026-10-25 |
| `br/public:avm/res/network/firewall-policy:<version>` | **0.3.6** | 2026-10-25 |
| `br/public:avm/res/network/public-ip-address:<version>` | **0.13.0** | 2026-10-25 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact versions. The policy is a
**separate module**: the firewall takes its id in `firewallPolicyId`.

**The two targets differ in shape.** The Bicep firewall module takes the *virtual network's* id in
`virtualNetworkResourceId` and finds `AzureFirewallSubnet` in it by its fixed name; the Terraform module
takes the subnet's id. Both are the same decision (`firewall_subnet`), rendered through what the module
asks for. The Bicep module creates its own public IP when none is given (`<name>-pip`), and a
management one with `enableManagementNic`; the render passes the addresses it created itself, so that
their names, zones and count follow the decisions.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide parameters

| Decision | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | On every module |
| `context.tags` | `tags` | |

### The call

```bicep
module firewallPolicy 'br/public:avm/res/network/firewall-policy:0.3.6' = {
  name: 'firewall-policy'
  params: {
    name: firewallPolicyName
    location: location
    tags: tags

    // decision: azure-firewall.firewall.sku_tier
    tier: 'Standard'

    // decision: azure-firewall.networking.dns_proxy, dns_servers
    enableProxy: true
    servers: []
    // decision: azure-firewall.networking.snat_private_ranges
    snat: {
      autoLearnPrivateRanges: 'Disabled'
      privateRanges: [ 'IANAPrivateRanges' ]
    }

    // decision: azure-firewall.security.threat_intelligence_mode
    threatIntelMode: 'Deny'
    // decision: azure-firewall.security.idps_mode - Premium only
    // intrusionDetection: { mode: 'Deny' }

    enableTelemetry: true
  }
}

module firewallPublicIps 'br/public:avm/res/network/public-ip-address:0.13.0' = [
  for i in range(0, publicIpCount): {
    name: 'firewall-pip-${i + 1}'
    params: {
      name: 'pip-${firewallName}-${i + 1}'
      location: location
      tags: tags
      skuName: 'Standard'
      publicIPAllocationMethod: 'Static'
      // decision: azure-firewall.firewall.zone_redundant
      availabilityZones: [ 1, 2, 3 ]
      enableTelemetry: true
    }
  }
]

module azureFirewall 'br/public:avm/res/network/azure-firewall:0.11.1' = {
  name: 'azure-firewall'
  params: {
    name: firewallName
    location: location
    tags: tags

    // decision: azure-firewall.firewall.sku_tier
    azureSkuTier: 'Standard'
    firewallPolicyId: firewallPolicy.outputs.resourceId
    // decision: azure-firewall.firewall.zone_redundant
    availabilityZones: [ 1, 2, 3 ]

    // decision: azure-firewall.firewall.firewall_subnet, public_ip_count
    virtualNetworkResourceId: virtualNetworkId
    publicIPResourceID: firewallPublicIps[0].outputs.resourceId
    additionalPublicIpConfigurations: [
      for i in range(1, publicIpCount - 1): {
        name: 'ipconfig-${i + 1}'
        properties: {
          publicIPAddress: { id: firewallPublicIps[i].outputs.resourceId }
        }
      }
    ]

    // decision: azure-firewall.networking.forced_tunneling
    enableManagementNic: false

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logAnalyticsDestinationType: 'Dedicated'
        logCategoriesAndGroups: [
          { category: 'AZFWNetworkRule' }
          { category: 'AZFWApplicationRule' }
          { category: 'AZFWNatRule' }
          { category: 'AZFWThreatIntel' }
          { category: 'AZFWDnsQuery' }
          { category: 'AZFWFqdnResolveFailure' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = azureFirewall.outputs.resourceId
output privateIp string = azureFirewall.outputs.privateIp
```

With `forced_tunneling: true` (always on `Basic`) the firewall gets `enableManagementNic: true` and
`managementIPAddressObject: { publicIPAllocationMethod: 'Static' }`. With `tls_inspection: true` the
policy gets `certificateName`, `keyVaultSecretId` and `managedIdentities: { userAssignedResourceIds }`,
and `intrusionDetection: { mode: 'Deny' }` is uncommented on `Premium`. `privateIp` is the address the
spokes' route tables and DNS settings point at.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy and each
public IP are their own nested deployments; the loop compiles to a `copy` whose expression text names
the literal.

## Authored rendering

The fallback. `Microsoft.Network/azureFirewalls` with `properties`, `Microsoft.Network/firewallPolicies`
and `Microsoft.Network/publicIPAddresses`.

What each decision renders to - the property and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.
