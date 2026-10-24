// Module "identity" (spec composition: identity) - the user-assigned identity of the app runtime.
// It exists before the app so that AcrPull and the data roles are in place at the first start.

@description('Finished identity name, assembled in main.bicep.')
param name string

@description('Azure region.')
param location string

@description('Tags applied to the identity.')
param tags object

@description('Role assignments on the identity itself, as { principalId, roleDefinitionId, principalType } (per stage, from the stage file).')
param roleAssignments array

// decision: user-assigned-identity.identity.federated_credentials - none.
var federatedCredentials = []

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: name
  location: location
  // decision: user-assigned-identity.identity.purpose
  tags: union(tags, { purpose: 'app-runtime' })

  properties: {
    // decision: user-assigned-identity.identity.isolation_scope
    isolationScope: 'None'
  }
}

// Credentials are written one after another: concurrent writes to one identity fail.
@batchSize(1)
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2024-11-30' = [
  for credential in federatedCredentials: {
    parent: identity
    name: credential.name
    properties: {
      issuer: credential.issuer
      subject: credential.subject
      audiences: credential.audiences
    }
  }
]

// decision: user-assigned-identity.identity.role_assignments
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for ra in roleAssignments: {
    name: guid(identity.id, ra.principalId, ra.roleDefinitionId)
    scope: identity
    properties: {
      principalId: ra.principalId
      principalType: ra.?principalType ?? 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', ra.roleDefinitionId)
    }
  }
]

output id string = identity.id
output name string = identity.name
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
