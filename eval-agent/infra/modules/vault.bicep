// Module "vault" (spec composition: vault) - key vault (RBAC), private endpoint, secret placeholder
// and diagnostics.
// Needs: network (subnet id), observability (workspace id). The private DNS zone id comes from the
// root, which owns the zones (wiring.private_dns_zones).

@description('Finished vault name, assembled in main.bicep (3-24 characters).')
param name string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Finished private endpoint name, assembled in main.bicep.')
param privateEndpointName string

@description('Resource id of the private endpoint subnet (network module output).')
param privateEndpointSubnetId string

@description('Resource id of the privatelink.vaultcore.azure.net zone (owned by the root).')
param privateDnsZoneId string

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Role assignments on the vault, as { principalId, roleDefinitionId, principalType } (per stage, from the stage file).')
param roleAssignments array

@description('Placeholder secrets that already exist; the pipeline fills this from a secret list before the deployment, so a placeholder never overwrites a real value with a new version.')
param existingSecretNames array = []

// decision: key-vault.security.secret_placeholders
var secretPlaceholders = ['entra-client-secret']

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: name
  location: location
  tags: tags

  properties: {
    tenantId: subscription().tenantId

    sku: {
      family: 'A'
      // decision: key-vault.vault.sku
      name: 'standard'
    }

    // decision: key-vault.vault.purge_protection - one-way, ARM rejects an explicit false.
    enablePurgeProtection: true
    enableSoftDelete: true
    // decision: key-vault.vault.soft_delete_retention_days
    softDeleteRetentionInDays: 90
    // decision: key-vault.vault.rbac_authorization
    enableRbacAuthorization: true

    // decision: key-vault.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      // decision: key-vault.networking.network_acl_bypass
      bypass: 'None'
      ipRules: []
      virtualNetworkRules: []
    }

    // decision: key-vault.security.enabled_for_services - none.
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
  }
}

// decision: key-vault.keys.key_management - platform_managed: no keys are created in the vault.

// A placeholder is created only while it does not exist yet. The secret is written through the
// management plane, so it works although the vault is closed to the public network.
resource placeholder 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = [
  for secretName in secretPlaceholders: if (!contains(existingSecretNames, secretName)) {
    parent: vault
    name: secretName
    properties: {
      value: 'placeholder - replace after deployment'
      contentType: 'placeholder'
    }
  }
]

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    // decision: key-vault.networking.private_endpoint_subnet - the subnet id is the private
    // endpoint subnet 'pe' selected in the network module.
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'psc-vault'
        properties: {
          privateLinkServiceId: vault.id
          groupIds: ['vault']
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
      { name: 'vaultcore', properties: { privateDnsZoneId: privateDnsZoneId } }
    ]
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: vault
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: key-vault.observability.diagnostic_categories
    logs: [
      { category: 'AuditEvent', enabled: true }
      { category: 'AzurePolicyEvaluationDetails', enabled: true }
    ]
    // decision: key-vault.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// decision: key-vault.identity.role_assignments
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for ra in roleAssignments: {
    name: guid(vault.id, ra.principalId, ra.roleDefinitionId)
    scope: vault
    properties: {
      principalId: ra.principalId
      principalType: ra.?principalType ?? 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ra.roleDefinitionId)
    }
  }
]

output id string = vault.id
output name string = vault.name
output vaultUri string = vault.properties.vaultUri
