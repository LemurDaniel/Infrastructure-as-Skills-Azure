// Rendered from infra-spec.yaml by infrastructure-as-skills-azure 0.5.4. Deployed.
targetScope = 'resourceGroup'

@description('Azure region of every resource.')
param location string = 'westeurope'

@description('Stage the parameter file deploys.')
@allowed(['development'])
param environment string

@description('Workload name in every resource name.')
param workload string = 'keepnames'

@description('Instance index in the names.')
param index int = 1

var locationCodes = {
  westeurope: 'we'
}
var environmentCodes = {
  development: 'dev'
}

var loc = locationCodes[location]
var env = environmentCodes[environment]
var idx = padLeft(index, 2, '0')
var uid4 = take(uniqueString(resourceGroup().id), 4)

// patterns.Azure."Microsoft.KeyVault/vaults": <TYPE>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>
var keyVaultName = 'kv-${env}-${workload}-${uid4}'
// patterns.Azure."Microsoft.Storage/storageAccounts": <TYPE><LOCATION><ENVIRONMENT><NAME><INDEX>, lowercase
var storageAccountName = toLower('st${loc}${env}${workload}${idx}')

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

output keyVaultName string = keyVault.name
output storageAccountName string = storageAccount.name
