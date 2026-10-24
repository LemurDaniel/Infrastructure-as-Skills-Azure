// Module "registry" (spec composition: registry) - container registry, private endpoint and diagnostics.
// Needs: network (subnet id), observability (workspace id). The private DNS zone ids come from the
// root, which owns the zones (wiring.private_dns_zones).

@description('Finished registry name, assembled in main.bicep.')
param name string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Finished private endpoint name, assembled in main.bicep.')
param privateEndpointName string

@description('Resource id of the private endpoint subnet (network module output).')
param privateEndpointSubnetId string

@description('Resource id of the privatelink.azurecr.io zone (owned by the root).')
param privateDnsZoneId string

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Additional regions as { location } (per stage, from the stage file).')
param geoReplicas array

@description('Role assignments on the registry, as { principalId, roleDefinitionId, principalType } (per stage, from the stage file).')
param roleAssignments array

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: name
  location: location
  tags: tags

  // decision: container-registry.registry.sku - Premium, forced by the private network exposure
  // (private endpoints need it).
  sku: { name: 'Premium' }

  // decision: container-registry.identity.managed_identity - none: the registry has no
  // identity block. Image pull is done by the app's identity.

  properties: {
    // decision: container-registry.registry.zone_redundant
    zoneRedundancy: 'Disabled'

    // decision: container-registry.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: container-registry.networking.network_rule_bypass
    networkRuleBypassOptions: 'None'

    // decision: container-registry.security.admin_enabled
    adminUserEnabled: false
    // decision: container-registry.security.anonymous_pull_enabled
    anonymousPullEnabled: false

    // decision: container-registry.security.key_management - platform_managed: no
    // properties.encryption block (customer-managed keys would be configured there).

    policies: {
      // decision: container-registry.registry.retention_untagged_days
      retentionPolicy: {
        days: 7
        status: 'enabled'
      }
      // decision: container-registry.networking.export_policy_enabled
      exportPolicy: {
        status: 'disabled'
      }
    }
  }
}

// decision: container-registry.registry.geo_replicas
resource replication 'Microsoft.ContainerRegistry/registries/replications@2025-04-01' = [
  for replica in geoReplicas: {
    parent: registry
    name: replica.location
    location: replica.location
    tags: tags
    properties: {
      zoneRedundancy: 'Disabled'
    }
  }
]

// decision: container-registry.networking.private_endpoint_subnet - the subnet id is the
// private endpoint subnet 'pe' selected in the network module.
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'psc-registry'
        properties: {
          privateLinkServiceId: registry.id
          groupIds: ['registry']
        }
      }
    ]
  }
}

// private_dns_ownership: deployment - this deployment writes the zone group.
resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'azurecr', properties: { privateDnsZoneId: privateDnsZoneId } }
    ]
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: registry
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: container-registry.observability.diagnostic_categories
    logs: [
      { category: 'ContainerRegistryRepositoryEvents', enabled: true }
      { category: 'ContainerRegistryLoginEvents', enabled: true }
    ]
    // decision: container-registry.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// decision: container-registry.identity.role_assignments
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for ra in roleAssignments: {
    name: guid(registry.id, ra.principalId, ra.roleDefinitionId)
    scope: registry
    properties: {
      principalId: ra.principalId
      principalType: ra.?principalType ?? 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ra.roleDefinitionId)
    }
  }
]

output id string = registry.id
output name string = registry.name
output loginServer string = registry.properties.loginServer
