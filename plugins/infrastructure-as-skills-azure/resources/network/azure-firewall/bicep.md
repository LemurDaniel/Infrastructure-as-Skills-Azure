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

| Decision | Parameter | Note |
|---|---|---|
| `sku_tier` | firewall `azureSkuTier`, policy `tier` | `'Basic'` / `'Standard'` / `'Premium'`, the same on both; module default `'Standard'` - written |
| `zone_redundant` | firewall `availabilityZones`; public IP `availabilityZones` | `[1, 2, 3]` or `[]`; module default all three |
| `firewall_subnet` | firewall `virtualNetworkResourceId` | The vnet; the module looks up `AzureFirewallSubnet` |
| `public_ip_count` | firewall `publicIPResourceID` (the first) and `additionalPublicIpConfigurations: [ { name, properties: { publicIPAddress: { id } } } ]` | One public IP module call per address |
| `forced_tunneling`, `management_subnet` | firewall `enableManagementNic: true` and `managementIPAddressObject` | The vnet needs `AzureFirewallManagementSubnet`; module default `false` - written |
| `dns_proxy`, `dns_servers` | policy `enableProxy`, `servers` | |
| `snat_private_ranges` | policy `snat: { autoLearnPrivateRanges, privateRanges }` | `autoLearnPrivateRanges` is required in the object: `'Disabled'` |
| `threat_intelligence_mode` | policy `threatIntelMode` | `'Off'` / `'Alert'` / `'Deny'`; module default `'Deny'` - written |
| `idps_mode` | policy `intrusionDetection: { mode }` | Premium only |
| `tls_inspection`, `tls_certificate_secret_id` | policy `certificateName`, `keyVaultSecretId` | Premium only |
| `policy_identity`, `user_assigned_identity_ids` | policy `managedIdentities: { userAssignedResourceIds }` | |
| `rule_collection_groups` | policy `ruleCollectionGroups`, or the child module `firewall-policy/rule-collection-group` | Wiring: filled by the pattern or the platform |
| `diagnostic_*`, `metrics_enabled` | firewall `diagnosticSettings: [ { workspaceResourceId, logAnalyticsDestinationType: 'Dedicated', logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy and each
public IP are their own nested deployments; the loop compiles to a `copy` whose expression text names
the literal.

## Authored rendering

The fallback. `Microsoft.Network/azureFirewalls` with `properties`, `Microsoft.Network/firewallPolicies`
and `Microsoft.Network/publicIPAddresses`:

| Decision | Property |
|---|---|
| `sku_tier`, `zone_redundant` | firewall `properties.sku: { name: 'AZFW_VNet', tier }` and `zones`; policy `properties.sku.tier` |
| `firewall_subnet`, `public_ip_count` | `properties.ipConfigurations[]: { name, properties: { subnet: { id }, publicIPAddress: { id } } }` - the subnet on the first entry only |
| `forced_tunneling` | `properties.managementIpConfiguration: { name, properties: { subnet: { id }, publicIPAddress: { id } } }` |
| `dns_proxy`, `dns_servers` | policy `properties.dnsSettings: { enableProxy, servers }` |
| `snat_private_ranges` | policy `properties.snat: { privateRanges, autoLearnPrivateRanges }` |
| `threat_intelligence_mode` | policy `properties.threatIntelMode` |
| `idps_mode` | policy `properties.intrusionDetection: { mode }` |
| `tls_inspection` | policy `properties.transportSecurity.certificateAuthority: { name, keyVaultSecretId }` and `identity` |
| `rule_collection_groups` | `Microsoft.Network/firewallPolicies/ruleCollectionGroups` |
