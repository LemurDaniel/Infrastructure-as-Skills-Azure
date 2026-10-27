// Module "storage" (spec composition: storage) - storage account, blob service settings, private
// endpoint and diagnostics.
// Needs: network (subnet id), observability (workspace id). The private DNS zone id comes from the
// root, which owns the zones (wiring.private_dns_zones).

@description('Finished storage account name, assembled in main.bicep (lowercase alphanumeric, max 24).')
param name string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Finished private endpoint name prefix, assembled in main.bicep; the sub-resource is appended.')
param privateEndpointNamePrefix string

@description('Index suffix of the private endpoint name (padded), assembled in main.bicep.')
param privateEndpointNameSuffix string

@description('Resource id of the private endpoint subnet (network module output).')
param privateEndpointSubnetId string

@description('Private DNS zone ids by sub-resource, e.g. { blob: <id> } (owned by the root).')
param privateDnsZoneIds object

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Role assignments on the account, as { principalId, roleDefinitionId, principalType } (per stage, from the stage file).')
param roleAssignments array

// decision: storage-account.networking.private_endpoint_subresources
var privateEndpointSubresources = ['blob']

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'

  sku: {
    // decision: storage-account.data_protection.replication
    name: 'Standard_LRS'
  }

  // decision: storage-account.identity.managed_identity - none: no identity block

  properties: {
    // decision: storage-account.security.min_tls_version
    minimumTlsVersion: 'TLS1_2'
    // decision: storage-account.security.https_traffic_only
    supportsHttpsTrafficOnly: true
    // decision: storage-account.security.allow_blob_public_access
    allowBlobPublicAccess: false
    // decision: storage-account.security.shared_access_key_enabled - access is via Entra ID and
    // RBAC; a key would bypass both.
    allowSharedKeyAccess: false
    // decision: storage-account.security.sftp_enabled
    isSftpEnabled: false

    // decision: storage-account.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // decision: storage-account.data_protection.access_tier
    accessTier: 'Hot'

    encryption: {
      // decision: storage-account.security.key_management - platform_managed
      keySource: 'Microsoft.Storage'
      // decision: storage-account.security.infrastructure_encryption_enabled - settable only at
      // creation; changing it later replaces the account.
      requireInfrastructureEncryption: true
      services: {
        blob: { enabled: true, keyType: 'Account' }
        file: { enabled: true, keyType: 'Account' }
      }
    }

    networkAcls: {
      defaultAction: 'Deny'
      // decision: storage-account.networking.allow_azure_services_bypass
      bypass: 'AzureServices'
    }

    // decision: storage-account.data_protection.immutability - none: no immutableStorageWithVersioning
    // block on the account.
  }
}

// Soft delete, versioning, change feed and point-in-time restore live on the blob service,
// not on the account. A setting with 0 days is rendered as disabled (enabled: true with 0 days is rejected).
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    // decision: storage-account.data_protection.blob_soft_delete_days - 0
    deleteRetentionPolicy: { enabled: false }
    // decision: storage-account.data_protection.container_soft_delete_days - 0
    containerDeleteRetentionPolicy: { enabled: false }
    // decision: storage-account.data_protection.versioning_enabled
    isVersioningEnabled: false
    // decision: storage-account.data_protection.change_feed_enabled
    changeFeed: { enabled: false }
    // decision: storage-account.data_protection.point_in_time_restore_days - 0
    restorePolicy: { enabled: false }
  }
}

// decision: blob-container.containers.container_names - one container for everything the apps share:
// the drift reports, fuzz/<id>/ (the fuzz reports), tune/<id>/ (the tuner's runs). The eval runs are not
// here: they live on the eval-history branch of the repository.
// decision: blob-container.placement.storage_account - a child of the account of this module.
var containerNames = ['results']

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = [
  for containerName in containerNames: {
    parent: blobService
    name: containerName
    properties: {
      // decision: blob-container.containers.public_access
      publicAccess: 'None'
      // decision: blob-container.containers.immutable_storage - false: no immutableStorageWithVersioning
      // block on the container.
      immutableStorageWithVersioning: { enabled: false }
      // decision: blob-container.containers.encryption_scope_locked - false: no scope is set and none locked,
      // so neither defaultEncryptionScope nor denyEncryptionScopeOverride is written (Azure takes both or none).
    }
  }
]

// decision: blob-container.identity.role_assignments - none on the container; the roles on the account
// (wiring.role_assignments) carry the access.

// One endpoint per sub-resource.
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = [
  for sub in privateEndpointSubresources: {
    name: '${privateEndpointNamePrefix}-${sub}-${privateEndpointNameSuffix}'
    location: location
    tags: tags
    properties: {
      // decision: storage-account.networking.private_endpoint_subnet - the subnet id is the
      // private endpoint subnet 'pe' selected in the network module.
      subnet: { id: privateEndpointSubnetId }
      privateLinkServiceConnections: [
        {
          name: 'psc-${sub}'
          properties: {
            privateLinkServiceId: storageAccount.id
            groupIds: [sub]
          }
        }
      ]
    }
  }
]

// private_dns_ownership: deployment - this deployment writes the zone group.
resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = [
  for (sub, i) in privateEndpointSubresources: {
    parent: privateEndpoint[i]
    name: 'default'
    properties: {
      privateDnsZoneConfigs: [
        { name: sub, properties: { privateDnsZoneId: privateDnsZoneIds[sub] } }
      ]
    }
  }
]

// The account itself emits metrics only.
resource accountDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: storageAccount
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: storage-account.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// Blob data-plane logs attach to the blob service; a setting on the account alone collects none.
resource blobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: blobService
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: storage-account.observability.diagnostic_categories
    logs: [
      { categoryGroup: 'audit', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// decision: storage-account.identity.role_assignments
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for ra in roleAssignments: {
    name: guid(storageAccount.id, ra.principalId, ra.roleDefinitionId)
    scope: storageAccount
    properties: {
      principalId: ra.principalId
      principalType: ra.?principalType ?? 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ra.roleDefinitionId)
    }
  }
]

output id string = storageAccount.id
output name string = storageAccount.name
