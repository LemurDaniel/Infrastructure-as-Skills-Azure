// Root of the claude-plugin-eval-agent deployment (rendered from infra-spec.yaml, target bicep).
// Scope: resource group. The pipeline deploys one stage at a time:
//   az deployment group create --subscription <subscriptionId> --resource-group <resourceGroupName> \
//     --template-file main.bicep --parameters main.<stage>.bicepparam
// Composition (granularity per-concern, authored resources): one file per module in modules/.
// This file holds the module calls and all wiring that spans two modules: the private DNS zones,
// the role assignments between modules and the diagnostics of the virtual network.

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------------------------
// Context parameters (no defaults; the values live in main.<stage>.bicepparam)
// ---------------------------------------------------------------------------------------------

@description('Azure region. Must be a key of locationCodes below; any other value (also the OPEN placeholder) fails the name assembly at deployment.')
param location string

@description('Workload short name, rendered into the resource names. The key vault name is the tightest limit (24 characters).')
@minLength(2)
param workload string

@description('Deployment stage. Drives the rendered names.')
@allowed(['production']) // keys of mappings.environment in use (context.environments)
param environment string

@description('Subscription the stage is deployed into. The pipeline uses the same value as the deployment target; here it seeds the globally unique name suffix.')
param subscriptionId string

@description('Resource group the stage is deployed into. The pipeline uses the same value as the deployment target; here it seeds the globally unique name suffix.')
param resourceGroupName string

// ---------------------------------------------------------------------------------------------
// Per-stage decisions (spec values keyed by stage)
// ---------------------------------------------------------------------------------------------

@description('Address space of the virtual network.')
param addressSpace string

@description('Subnets as { name, prefix }.')
param subnets array

@description('Prefix of the subnet that hosts the private endpoints.')
param privateEndpointSubnetPrefix string

@description('Additional registry regions as { location }.')
param registryGeoReplicas array

@description('Role assignments on the user-assigned identity itself, as { principalId, roleDefinitionId, principalType }.')
param identityRoleAssignments array

@description('Role assignments on the registry, as { principalId, roleDefinitionId, principalType }.')
param registryRoleAssignments array

@description('Role assignments on the Foundry account, as { principalId, roleDefinitionId, principalType }.')
param foundryRoleAssignments array

@description('Role assignments on the storage account, as { principalId, roleDefinitionId, principalType }.')
param storageRoleAssignments array

@description('Role assignments on the key vault, as { principalId, roleDefinitionId, principalType }.')
param vaultRoleAssignments array

// ---------------------------------------------------------------------------------------------
// Open points of the spec and application inputs (placeholders in the stage file until answered)
// ---------------------------------------------------------------------------------------------

@description('Bootstrap image as name:tag without the registry, no latest; used only on the first deployment, the image pipeline owns the image afterwards (spec: resources.app-service.runtime.container_image_owner).')
param containerImage string

@description('linuxFxVersion the web app runs now; the pipeline fills this from the live web app before the deployment so the image is never rolled back. Empty on the first deployment.')
param existingLinuxFxVersion string = ''

@description('Model deployments as { name, model: { format, name, version } } (spec open: resources.foundry.models.model_deployments).')
param modelDeployments array

@description('Where the agent fetches the Claude plugin from (spec open: application.plugin_source).')
param pluginSource string

@description('Client id of the existing Entra app registration used for the sign-in.')
param entraClientId string

@description('Tenant id of the Entra tenant that signs users in.')
param entraTenantId string

// ---------------------------------------------------------------------------------------------
// Optional
// ---------------------------------------------------------------------------------------------

@description('Instance number, for a second deployment beside the first.')
param index int = 1

@description('Tags applied to every resource. The spec carries no tag decision, so the default is empty.')
param tags object = {}

@description('Names of placeholder secrets that already exist in the vault; the pipeline fills this from a secret list before the deployment so a placeholder never overwrites a real value.')
param existingSecretNames array = []

// ---------------------------------------------------------------------------------------------
// Names, assembled from naming.default.yaml (deployment.naming_convention: default)
// ---------------------------------------------------------------------------------------------

// Generated from the convention (mappings). Regenerate, do not edit here.
var environmentCodes = {
  production: 'prod'
}
var locationCodes = {
  westeurope: 'we'
  northeurope: 'ne'
  germanywestcentral: 'gwc'
  francecentral: 'frc'
  swedencentral: 'sdc'
}

var loc = locationCodes[location]
var env = environmentCodes[environment]
var idx = padLeft(index, 2, '0')
// <UNIQUE_ID_4>: subscription, resource group and instance number. The instance number is in the seed
// so a new instance gets new globally unique names (a deleted vault keeps its name until purged).
var unique4 = take(uniqueString(subscriptionId, resourceGroupName, idx), 4)

// <TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<INDEX>
var virtualNetworkName = 'vnet-${loc}-${env}-${workload}-${idx}'
var workspaceName = 'log-${loc}-${env}-${workload}-${idx}'
var identityName = 'id-${loc}-${env}-${workload}-${idx}'
var planName = 'plan-${loc}-${env}-${workload}-${idx}'
var appName = 'app-${loc}-${env}-${workload}-${idx}'
// <TYPE><LOCATION><ENVIRONMENT><NAME><INDEX>, lowercase, alphanumeric only
var registryName = toLower('cr${loc}${env}${workload}${idx}')
var storageAccountName = toLower('st${loc}${env}${workload}${idx}')
// <TYPE>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>
var foundryName = 'aif-${env}-${workload}-${unique4}'
var vaultName = 'kv-${env}-${workload}-${unique4}'
// <TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<SUBNAME>-<INDEX>
var privateEndpointNamePrefix = 'pep-${loc}-${env}-${workload}'
var registryPrivateEndpointName = '${privateEndpointNamePrefix}-registry-${idx}'
var foundryPrivateEndpointName = '${privateEndpointNamePrefix}-account-${idx}'
var vaultPrivateEndpointName = '${privateEndpointNamePrefix}-vault-${idx}'
var dnsLinkName = 'vnl-${loc}-${env}-${workload}-${idx}'

// Subnet names (spec: virtual-network.addressing.subnets, resources.*.networking.private_endpoint_subnet,
// app-service.networking.integration_subnet).
var privateEndpointSubnetName = 'pe'
var integrationSubnetName = 'app-integration'

// ---------------------------------------------------------------------------------------------
// Built-in role definitions (the same GUIDs in every tenant)
// ---------------------------------------------------------------------------------------------

var roleDefinitionIds = {
  AcrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'Storage Blob Data Contributor': 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  'Azure AI User': '53ca6127-db72-4b80-b1b0-d745d6d5456d'
  'Key Vault Secrets User': '4633458b-17de-408a-b874-0445c86b69e6'
}

// ---------------------------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------------------------

module network 'modules/network.bicep' = {
  name: 'network'
  params: {
    name: virtualNetworkName
    location: location
    tags: tags
    addressSpace: addressSpace
    subnets: subnets
    privateEndpointSubnetName: privateEndpointSubnetName
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
    integrationSubnetName: integrationSubnetName
  }
}

module observability 'modules/observability.bicep' = {
  name: 'observability'
  params: {
    name: workspaceName
    location: location
    tags: tags
  }
}

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    name: identityName
    location: location
    tags: tags
    roleAssignments: identityRoleAssignments
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    name: registryName
    location: location
    tags: tags
    privateEndpointName: registryPrivateEndpointName
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    privateDnsZoneId: resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.registry)
    diagnosticWorkspaceId: observability.outputs.id
    geoReplicas: registryGeoReplicas
    roleAssignments: registryRoleAssignments
  }
  dependsOn: [
    // The zone group of the private endpoint needs the zone (and its link) to exist.
    privateDnsZoneLinks
  ]
}

module ai 'modules/ai.bicep' = {
  name: 'ai'
  params: {
    name: foundryName
    location: location
    tags: tags
    privateEndpointName: foundryPrivateEndpointName
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    privateDnsZoneIds: [
      resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.cognitiveservices)
      resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.openai)
      resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.aiservices)
    ]
    diagnosticWorkspaceId: observability.outputs.id
    modelDeployments: modelDeployments
    roleAssignments: foundryRoleAssignments
  }
  dependsOn: [
    privateDnsZoneLinks
  ]
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: storageAccountName
    location: location
    tags: tags
    privateEndpointNamePrefix: privateEndpointNamePrefix
    privateEndpointNameSuffix: idx
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    privateDnsZoneIds: {
      blob: resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.blob)
    }
    diagnosticWorkspaceId: observability.outputs.id
    roleAssignments: storageRoleAssignments
  }
  dependsOn: [
    privateDnsZoneLinks
  ]
}

module vault 'modules/vault.bicep' = {
  name: 'vault'
  params: {
    name: vaultName
    location: location
    tags: tags
    privateEndpointName: vaultPrivateEndpointName
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    privateDnsZoneId: resourceId('Microsoft.Network/privateDnsZones', privateDnsZoneNames.vault)
    diagnosticWorkspaceId: observability.outputs.id
    roleAssignments: vaultRoleAssignments
    existingSecretNames: existingSecretNames
  }
  dependsOn: [
    privateDnsZoneLinks
  ]
}

module app 'modules/app.bicep' = {
  name: 'app'
  params: {
    planName: planName
    appName: appName
    location: location
    tags: tags
    integrationSubnetId: network.outputs.integrationSubnetId
    diagnosticWorkspaceId: observability.outputs.id
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    registryLoginServer: registry.outputs.loginServer
    vaultUri: vault.outputs.vaultUri
    foundryEndpoint: ai.outputs.endpoint
    storageAccountName: storage.outputs.name
    containerImage: containerImage
    existingLinuxFxVersion: existingLinuxFxVersion
    pluginSource: pluginSource
    entraClientId: entraClientId
    entraTenantId: entraTenantId
  }
  dependsOn: [
    // The roles must be effective before the container first starts (image pull, secret reference).
    // Bicep cannot see this: the app module takes no output of the role assignments.
    acrPullAssignment
    storageBlobAssignment
    foundryUserAssignment
    keyVaultSecretsAssignment
  ]
}

// ---------------------------------------------------------------------------------------------
// Wiring: private DNS (wiring.private_dns_zones, deployment.private_dns_ownership: deployment)
// ---------------------------------------------------------------------------------------------

// Zone names are fixed by wiring.private_dns_zones (public cloud).
var privateDnsZoneNames = {
  vault: 'privatelink.vaultcore.azure.net'
  #disable-next-line no-hardcoded-env-urls
  blob: 'privatelink.blob.core.windows.net'
  registry: 'privatelink.azurecr.io'
  cognitiveservices: 'privatelink.cognitiveservices.azure.com'
  openai: 'privatelink.openai.azure.com'
  aiservices: 'privatelink.services.ai.azure.com'
}

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = [
  for zone in items(privateDnsZoneNames): {
    name: zone.value
    location: 'global'
    tags: tags
  }
]

resource privateDnsZoneLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [
  for (zone, i) in items(privateDnsZoneNames): {
    parent: privateDnsZone[i]
    name: dnsLinkName
    location: 'global'
    tags: tags
    properties: {
      registrationEnabled: false
      virtualNetwork: { id: network.outputs.id }
    }
  }
]

// ---------------------------------------------------------------------------------------------
// Wiring: role assignments between modules (wiring.role_assignments), all to the user-assigned identity
// ---------------------------------------------------------------------------------------------

resource registryRef 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: registryName
}

resource storageAccountRef 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageAccountName
}

resource foundryRef 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource vaultRef 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: vaultName
}

resource identityRef 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' existing = {
  name: identityName
}

// wiring.role_assignments: user-assigned-identity -> container-registry, AcrPull
resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registryRef.id, identityRef.id, roleDefinitionIds.AcrPull)
  scope: registryRef
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionIds.AcrPull)
  }
  dependsOn: [
    // The scope is an existing reference: Bicep cannot see that the registry module creates it.
    registry
  ]
}

// wiring.role_assignments: user-assigned-identity -> storage-account, Storage Blob Data Contributor
resource storageBlobAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountRef.id, identityRef.id, roleDefinitionIds['Storage Blob Data Contributor'])
  scope: storageAccountRef
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleDefinitionIds['Storage Blob Data Contributor']
    )
  }
  dependsOn: [
    storage
  ]
}

// wiring.role_assignments: user-assigned-identity -> foundry, Azure AI User (the tenant now calls
// this role 'Foundry User'; the role definition GUID is the same)
resource foundryUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryRef.id, identityRef.id, roleDefinitionIds['Azure AI User'])
  scope: foundryRef
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleDefinitionIds['Azure AI User']
    )
  }
  dependsOn: [
    ai
  ]
}

// wiring.role_assignments: user-assigned-identity -> key-vault, Key Vault Secrets User
resource keyVaultSecretsAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vaultRef.id, identityRef.id, roleDefinitionIds['Key Vault Secrets User'])
  scope: vaultRef
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roleDefinitionIds['Key Vault Secrets User']
    )
  }
  dependsOn: [
    vault
  ]
}

// ---------------------------------------------------------------------------------------------
// Wiring: diagnostics of the virtual network (the network module does not need the workspace)
// ---------------------------------------------------------------------------------------------

resource virtualNetworkRef 'Microsoft.Network/virtualNetworks@2025-01-01' existing = {
  name: virtualNetworkName
}

resource virtualNetworkDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: virtualNetworkRef
  properties: {
    // decision: virtual-network.observability.diagnostic_workspace
    workspaceId: observability.outputs.id
    logs: [
      { categoryGroup: 'allLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
  dependsOn: [
    // The scope is an existing reference: Bicep cannot see that the network module creates it.
    network
  ]
}

// decision: virtual-network.observability.flow_logs_enabled - false: no flow log resource (a
// Network Watcher flow log would be rendered here).

// ---------------------------------------------------------------------------------------------
// Outputs (nothing secret)
// ---------------------------------------------------------------------------------------------

output appId string = app.outputs.id
output appDefaultHostname string = app.outputs.defaultHostname
output registryLoginServer string = registry.outputs.loginServer
output vaultUri string = vault.outputs.vaultUri
output foundryEndpoint string = ai.outputs.endpoint
output storageAccountName string = storage.outputs.name
