// Module "network" (spec composition: network) - virtual network with its subnets.
// Authored resources, no AVM module call (deployment.module_source: authored).

@description('Finished virtual network name, assembled in main.bicep.')
param name string

@description('Azure region.')
param location string

@description('Tags applied to the virtual network.')
param tags object

@description('Address space of the virtual network (per stage, from the stage file).')
param addressSpace string

@description('Subnets as { name, prefix } (per stage, from the stage file).')
param subnets array

@description('Name of the subnet that hosts the private endpoints.')
param privateEndpointSubnetName string

@description('Prefix of the subnet that hosts the private endpoints (per stage, from the stage file).')
param privateEndpointSubnetPrefix string

@description('Name of the subnet the app service integrates into (delegated).')
param integrationSubnetName string

// decision: virtual-network.addressing.dns_servers - empty list: Azure-provided DNS, so the
// privatelink zones resolve without forwarders.
var dnsServers = []

// decision: virtual-network.subnet_policy.private_endpoint_network_policies
var privateEndpointNetworkPolicies = 'Enabled'

// decision: virtual-network.subnet_policy.service_endpoints - none on any subnet.
var serviceEndpoints = []

// decision: virtual-network.subnet_policy.subnet_delegations
var subnetDelegations = [
  { subnet: 'app-integration', service: 'Microsoft.Web/serverFarms' }
]

// Nested loops are not allowed here, so the inner lists use map() and filter().
var subnetDefinitions = [
  for subnet in subnets: {
    name: subnet.name
    properties: {
      addressPrefix: subnet.prefix
      // NSG and routes apply to private endpoint traffic.
      privateEndpointNetworkPolicies: privateEndpointNetworkPolicies
      serviceEndpoints: map(serviceEndpoints, service => { service: service })
      delegations: map(
        filter(subnetDelegations, d => d.subnet == subnet.name),
        d => { name: 'delegation', properties: { serviceName: d.service } }
      )
    }
  }
]

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2025-01-01' = {
  name: name
  location: location
  tags: tags

  properties: {
    addressSpace: {
      addressPrefixes: [addressSpace]
    }

    dhcpOptions: {
      dnsServers: dnsServers
    }

    // decision: virtual-network.security.ddos_protection - no DDoS protection plan.
    enableDdosProtection: false

    // Subnets are declared inline: a separate child resource would be removed again by the
    // next PUT of the virtual network.
    subnets: subnetDefinitions
  }
}

// The subnet is picked by name AND prefix: a stage file whose private-endpoint prefix does not
// match the subnet list fails here (empty result) instead of silently using another subnet.
var privateEndpointSubnet = filter(
  virtualNetwork.properties.subnets,
  s => s.name == privateEndpointSubnetName && s.properties.addressPrefix == privateEndpointSubnetPrefix
)[0]
var integrationSubnet = filter(virtualNetwork.properties.subnets, s => s.name == integrationSubnetName)[0]

output id string = virtualNetwork.id
output name string = virtualNetwork.name
output integrationSubnetId string = integrationSubnet.id
output privateEndpointSubnetId string = privateEndpointSubnet.id
