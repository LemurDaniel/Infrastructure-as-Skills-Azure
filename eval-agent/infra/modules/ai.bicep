// Module "ai" (spec composition: ai) - AI Foundry account (AIServices), its projects, model
// deployments, private endpoint and diagnostics.
// Needs: network (subnet id), observability (workspace id). The private DNS zone ids come from the
// root, which owns the zones (wiring.private_dns_zones).

@description('Finished account name, assembled in main.bicep. It is also the custom subdomain.')
param name string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Finished private endpoint name, assembled in main.bicep.')
param privateEndpointName string

@description('Resource id of the private endpoint subnet (network module output).')
param privateEndpointSubnetId string

@description('Resource ids of the cognitiveservices, openai and services.ai private DNS zones (owned by the root).')
param privateDnsZoneIds array

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Model deployments as { name, model: { format, name, version } } (OPEN in the stage file until the workload owner names them).')
param modelDeployments array

@description('Role assignments on the account, as { principalId, roleDefinitionId, principalType } (per stage, from the stage file).')
param roleAssignments array

// decision: foundry.account.projects
var projects = ['eval']

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  tags: tags

  // decision: foundry.account.kind
  kind: 'AIServices'
  // decision: foundry.account.sku_name
  sku: { name: 'S0' }

  // decision: foundry.identity.managed_identity - none: no identity block

  properties: {
    // The subdomain is required for token authentication and private endpoints, and cannot be changed.
    customSubDomainName: name

    // decision: foundry.account.project_management
    allowProjectManagement: true

    // decision: foundry.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: foundry.networking.restrict_outbound
    restrictOutboundNetworkAccess: true
    allowedFqdnList: []

    // decision: foundry.security.local_authentication_disabled
    disableLocalAuth: true

    // decision: foundry.security.key_management - platform_managed: no properties.encryption
    // block (customer-managed keys would be configured there).
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = [
  for projectName in projects: {
    parent: account
    name: projectName
    location: location
    tags: tags
    identity: { type: 'SystemAssigned' }
    properties: {}
  }
]

// Deployments are created one after another: parallel creation returns 409 Conflict.
// The model and version come from the stage file (open: resources.foundry.models.model_deployments);
// SKU, capacity, upgrade behaviour and content filter are decisions and fixed here.
@batchSize(1)
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [
  for deployment in modelDeployments: {
    parent: account
    name: deployment.name
    sku: {
      // decision: foundry.models.deployment_sku
      name: 'DataZoneStandard'
      // decision: foundry.models.deployment_capacity
      capacity: 10
    }
    properties: {
      model: deployment.model
      // decision: foundry.models.version_upgrade_option
      versionUpgradeOption: 'OnceCurrentVersionExpired'
      // decision: foundry.models.content_filter
      raiPolicyName: 'Microsoft.DefaultV2'
    }
  }
]

// decision: foundry.networking.private_endpoint_subnet - the subnet id is the private endpoint
// subnet 'pe' selected in the network module.
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'psc-account'
        properties: {
          privateLinkServiceId: account.id
          groupIds: ['account']
        }
      }
    ]
  }
}

// private_dns_ownership: deployment - this deployment writes the zone group. An AIServices account
// answers under three hostnames, so the group holds three zones.
resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      for (zoneId, i) in privateDnsZoneIds: {
        name: 'zone${i}'
        properties: { privateDnsZoneId: zoneId }
      }
    ]
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: account
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: foundry.observability.diagnostic_categories
    logs: [
      { category: 'Audit', enabled: true }
      { category: 'RequestResponse', enabled: true }
      { category: 'AzureOpenAIRequestUsage', enabled: true }
    ]
    // decision: foundry.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// decision: foundry.identity.role_assignments
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for ra in roleAssignments: {
    name: guid(account.id, ra.principalId, ra.roleDefinitionId)
    scope: account
    properties: {
      principalId: ra.principalId
      principalType: ra.?principalType ?? 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ra.roleDefinitionId)
    }
  }
]

output id string = account.id
output name string = account.name
output endpoint string = account.properties.endpoint
