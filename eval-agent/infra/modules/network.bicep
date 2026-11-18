// Module "network" (spec composition: network) - virtual network with its subnets and the
// network security group of each subnet.
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

@description('Finished name of the network security group on the private endpoint subnet, assembled in main.bicep.')
param endpointsSecurityGroupName string

@description('Finished name of the network security group on the app integration subnet, assembled in main.bicep.')
param appsSecurityGroupName string

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

// Network security groups. Every rule is written inline in properties.securityRules, never as a
// child resource: mixing the two makes a redeploy remove one or the other.

// decision: network-security-group__endpoints.rules.subnet_purpose - private_endpoints: the
// baseline lets the virtual network reach the endpoints on 443, the port of every service behind
// an endpoint here (registry, Foundry, blob, key vault, the app services).
var endpointsBaselineRules = [
  {
    name: 'allow-vnet-https-inbound'
    properties: {
      priority: 100
      direction: 'Inbound'
      access: 'Allow'
      protocol: 'Tcp'
      sourceAddressPrefix: 'VirtualNetwork'
      sourcePortRange: '*'
      destinationAddressPrefix: privateEndpointSubnetPrefix
      destinationPortRange: '443'
    }
  }
]

// decision: network-security-group__endpoints.rules.rules - no customer rules.
var endpointsCustomRules = []

// decision: network-security-group__endpoints.rules.default_inbound - explicit, so it shows in the plan.
var endpointsDefaultInboundRules = [
  {
    name: 'deny-all-inbound'
    properties: {
      priority: 4096
      direction: 'Inbound'
      access: 'Deny'
      protocol: '*'
      sourceAddressPrefix: '*'
      sourcePortRange: '*'
      destinationAddressPrefix: '*'
      destinationPortRange: '*'
    }
  }
]

// decision: network-security-group__endpoints.rules.default_outbound - deny_internet: nothing
// leaves the endpoint subnet for the internet.
var endpointsDefaultOutboundRules = [
  {
    name: 'deny-internet-outbound'
    properties: {
      priority: 4096
      direction: 'Outbound'
      access: 'Deny'
      protocol: '*'
      sourceAddressPrefix: '*'
      sourcePortRange: '*'
      destinationAddressPrefix: 'Internet'
      destinationPortRange: '*'
    }
  }
]

// decision: network-security-group__apps.rules.subnet_purpose - app_integration: the integration
// is outbound only, so no baseline inbound rule; outbound stays with the Azure default rules.
var appsBaselineRules = []

// decision: network-security-group__apps.rules.rules - no customer rules.
var appsCustomRules = []

// decision: network-security-group__apps.rules.default_inbound - explicit, so it shows in the plan.
var appsDefaultInboundRules = [
  {
    name: 'deny-all-inbound'
    properties: {
      priority: 4096
      direction: 'Inbound'
      access: 'Deny'
      protocol: '*'
      sourceAddressPrefix: '*'
      sourcePortRange: '*'
      destinationAddressPrefix: '*'
      destinationPortRange: '*'
    }
  }
]

// decision: network-security-group__apps.rules.default_outbound - azure_default: no rule, the
// built-in outbound rules apply (the apps call github.com outside the virtual network).
var appsDefaultOutboundRules = []

resource endpointsSecurityGroup 'Microsoft.Network/networkSecurityGroups@2025-01-01' = {
  name: endpointsSecurityGroupName
  location: location
  tags: tags

  properties: {
    securityRules: concat(
      endpointsBaselineRules,
      endpointsCustomRules,
      endpointsDefaultInboundRules,
      endpointsDefaultOutboundRules
    )
  }
}

resource appsSecurityGroup 'Microsoft.Network/networkSecurityGroups@2025-01-01' = {
  name: appsSecurityGroupName
  location: location
  tags: tags

  properties: {
    securityRules: concat(appsBaselineRules, appsCustomRules, appsDefaultInboundRules, appsDefaultOutboundRules)
  }
}

// decision: network-security-group__endpoints.networking.subnets, network-security-group__apps.networking.subnets
// The association is made on the subnet (an NSG has no property naming its subnets). A subnet in
// the stage file without an entry here fails the deployment instead of going unprotected.
var subnetSecurityGroupIds = {
  '${privateEndpointSubnetName}': endpointsSecurityGroup.id
  '${integrationSubnetName}': appsSecurityGroup.id
}

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
      networkSecurityGroup: {
        id: subnetSecurityGroupIds[subnet.name]
      }
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
