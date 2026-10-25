// Module "app" (spec composition: app) - one Linux App Service plan and three container web apps on it:
//   dashboard - internet-facing, Entra sign-in (authsettingsV2), reads the results, files the tickets
//   agent     - not reachable from outside, runs the evals, writes the results; holds no secret
//   drift     - not reachable from outside, compares the pinned AVM versions with the current ones and
//               opens a pull request; reads its GitHub token from the vault and reaches the AVM sources
//               on the internet (allowlist enforced in code only, spec open application.drift_internet_allowlist)
// All have VNet integration and diagnostics.
// The agent and the drift watcher have a private endpoint each (the dashboard starts a run through
// them); the root owns the zone.
// Needs: network (integration and private endpoint subnet), observability (workspace), identity-dashboard,
// identity-agent and identity-drift (user-assigned), registry (login server), vault (vault URI for the
// secret references), ai (endpoint), storage (account name).
// The question set renders one site per plan; the shared plan is rendered once here and the agent's
// and the drift watcher's sites are rendered by hand from the same decisions (spec: app-service__agent.hosting,
// app-service__drift.hosting).

@description('Finished plan name, assembled in main.bicep.')
param planName string

@description('Finished name of the dashboard app, assembled in main.bicep. It is the public hostname.')
param dashboardAppName string

@description('Finished name of the agent app, assembled in main.bicep.')
param agentAppName string

@description('Finished name of the drift watcher app, assembled in main.bicep.')
param driftAppName string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Resource id of the delegated integration subnet (network module output).')
param integrationSubnetId string

@description('Resource id of the private endpoint subnet (network module output); the agent is reachable only through its private endpoint there.')
param privateEndpointSubnetId string

@description('Finished name of the agent private endpoint, assembled in main.bicep.')
param agentPrivateEndpointName string

@description('Finished name of the drift watcher private endpoint, assembled in main.bicep.')
param driftPrivateEndpointName string

@description('Resource id of the privatelink.azurewebsites.net zone (owned by the root).')
param privateDnsZoneId string

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Resource id of the dashboard identity (identity-dashboard module output).')
param dashboardIdentityId string

@description('Client id of the dashboard identity (identity-dashboard module output).')
param dashboardIdentityClientId string

@description('Resource id of the agent identity (identity-agent module output).')
param agentIdentityId string

@description('Client id of the agent identity (identity-agent module output).')
param agentIdentityClientId string

@description('Resource id of the drift watcher identity (identity-drift module output).')
param driftIdentityId string

@description('Client id of the drift watcher identity (identity-drift module output).')
param driftIdentityClientId string

@description('Login server of the container registry (registry module output).')
param registryLoginServer string

@description('Vault URI (vault module output); the dashboard reads the client secret and the GitHub token, the drift watcher its own GitHub token from there through Key Vault references.')
param vaultUri string

@description('Endpoint of the Foundry account (ai module output); the agent and the drift watcher call the models there.')
param foundryEndpoint string

@description('Name of the storage account (storage module output); the dashboard reads and the agent writes eval results there, the drift watcher writes its reports.')
param storageAccountName string

@description('Bootstrap image of the dashboard as name:tag, without the registry; used only while the app has no image yet. After that the image belongs to the separate image pipeline (no latest).')
param dashboardContainerImage string

@description('Bootstrap image of the agent as name:tag, without the registry; used only while the app has no image yet. After that the image belongs to the separate image pipeline (no latest).')
param agentContainerImage string

@description('Bootstrap image of the drift watcher as name:tag, without the registry; used only while the app has no image yet. After that the image belongs to the separate image pipeline (no latest).')
param driftContainerImage string

@description('linuxFxVersion the dashboard runs now (DOCKER|<registry>/<name>:<tag>), read by the pipeline before the deployment; empty on the first deployment. Kept as is so this template never rolls the image back.')
param existingDashboardLinuxFxVersion string = ''

@description('linuxFxVersion the agent runs now (DOCKER|<registry>/<name>:<tag>), read by the pipeline before the deployment; empty on the first deployment. Kept as is so this template never rolls the image back.')
param existingAgentLinuxFxVersion string = ''

@description('linuxFxVersion the drift watcher runs now (DOCKER|<registry>/<name>:<tag>), read by the pipeline before the deployment; empty on the first deployment. Kept as is so this template never rolls the image back.')
param existingDriftLinuxFxVersion string = ''

@description('When the drift watcher runs its check (OPEN in the stage file, spec open: application.drift_schedule).')
param driftSchedule string

@description('Where the agent fetches the Claude plugin from (OPEN in the stage file).')
param pluginSource string

@description('Client id of the existing Entra app registration used for the dashboard sign-in (stage file).')
param entraClientId string

@description('Tenant id of the Entra tenant that signs users in (stage file).')
param entraTenantId string

// decision: key-vault.security.secret_placeholders - the names of the secrets the dashboard reads.
var clientSecretName = 'entra-client-secret'
var clientSecretSettingName = 'MICROSOFT_PROVIDER_AUTHENTICATION_SECRET'
var githubTokenSecretName = 'github-token'
// decision: key-vault.security.secret_placeholders - the drift watcher's own GitHub token.
var driftGithubTokenSecretName = 'github-drift-token'

// The internet hosts the drift watcher may reach. App Service does not filter outbound traffic, so the
// list is enforced in the watcher's code only (spec open: application.drift_internet_allowlist).
var driftAllowedHosts = ['github.com', 'api.github.com', 'raw.githubusercontent.com', 'mcr.microsoft.com', 'azure.github.io']

resource plan 'Microsoft.Web/serverFarms@2024-11-01' = {
  name: planName
  location: location
  tags: tags
  // decision: app-service__dashboard.hosting.os_type (the agent follows it)
  kind: 'linux'
  sku: {
    // decision: app-service__dashboard.hosting.sku (the agent follows it)
    name: 'B2'
    // decision: app-service__dashboard.hosting.instance_count (the agent follows it)
    capacity: 1
  }
  properties: {
    // decision: app-service__dashboard.hosting.os_type - reserved is what makes the plan Linux.
    reserved: true
    // decision: app-service__dashboard.hosting.zone_redundant (the agent follows it)
    zoneRedundant: false
  }
}

// ---------------------------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------------------------

resource dashboard 'Microsoft.Web/sites@2024-11-01' = {
  name: dashboardAppName
  location: location
  tags: tags
  // decision: app-service__dashboard.runtime.runtime_stack - container
  kind: 'app,linux,container'

  // decision: app-service__dashboard.identity.managed_identity - user-assigned, so that AcrPull and
  // the data roles exist before the container first starts.
  // decision: app-service__dashboard.identity.user_assigned_identity_ids
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${dashboardIdentityId}': {}
    }
  }

  properties: {
    serverFarmId: plan.id

    // decision: app-service__dashboard.security.https_only
    httpsOnly: true

    // decision: app-service__dashboard.networking.public_network_access - the dashboard is internet-facing.
    publicNetworkAccess: 'Enabled'

    // decision: app-service__dashboard.networking.vnet_integration / app-service__dashboard.networking.integration_subnet
    virtualNetworkSubnetId: integrationSubnetId
    // decision: app-service__dashboard.networking.vnet_route_all
    outboundVnetRouting: {
      allTraffic: false
    }

    // Key Vault references are resolved with the user-assigned identity, not the (absent) system one.
    keyVaultReferenceIdentity: dashboardIdentityId

    siteConfig: {
      // decision: app-service__dashboard.runtime.container_image_owner - the image is set here only on
      // the first deployment; later the image pipeline owns it and this keeps what runs.
      linuxFxVersion: !empty(existingDashboardLinuxFxVersion) ? existingDashboardLinuxFxVersion : 'DOCKER|${registryLoginServer}/${dashboardContainerImage}'
      // Image pull with the managed identity instead of registry credentials.
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: dashboardIdentityClientId

      // decision: app-service__dashboard.runtime.always_on
      alwaysOn: true
      // decision: app-service__dashboard.runtime.http2_enabled
      http20Enabled: true
      // decision: app-service__dashboard.security.ftps_state
      ftpsState: 'Disabled'
      // decision: app-service__dashboard.security.min_tls_version - the Kudu/SCM site gets the same minimum.
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      // decision: app-service__dashboard.runtime.health_check_path - empty: no healthCheckPath is rendered
      // (a path that does not return 2xx would mark the whole plan unhealthy).

      appSettings: [
        // The sign-in's client secret: a Key Vault reference, never a value.
        {
          name: clientSecretSettingName
          value: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/${clientSecretName}/)'
        }
        // The token the dashboard files tickets with (issues:write on this repository only).
        {
          name: 'GITHUB_TOKEN'
          value: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/${githubTokenSecretName}/)'
        }
        // DefaultAzureCredential needs the client id to pick the user-assigned identity.
        { name: 'AZURE_CLIENT_ID', value: dashboardIdentityClientId }
        // The registry is reachable only through its private endpoint, so the platform's image pull
        // must go through the VNet integration. The site property vnetImagePullEnabled is not in the
        // type definition of API 2024-11-01 (bicep build rejects it), hence the app setting.
        { name: 'WEBSITE_PULL_IMAGE_OVER_VNET', value: 'true' }
        { name: 'STORAGE_ACCOUNT_NAME', value: storageAccountName }
      ]
    }
  }
}

// decision: app-service__dashboard.security.basic_auth_enabled - two switches, FTP and SCM.
resource dashboardBasicAuthFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: dashboard
  name: 'ftp'
  properties: { allow: false }
}

resource dashboardBasicAuthScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: dashboard
  name: 'scm'
  properties: { allow: false }
}

// Hand-rendered (no question set): sign-in with the existing Entra app registration. Anonymous
// requests are redirected to the login. The redirect URI
// https://<app host>/.auth/login/aad/callback is registered by the identity team after the first
// deployment (spec open: resources.app-service__dashboard.identity.entra_sign_in).
// decision: app-service__dashboard.identity.entra_sign_in
resource dashboardAuthSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  parent: dashboard
  name: 'authsettingsV2'
  properties: {
    platform: {
      enabled: true
      runtimeVersion: '~1'
    }
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          openIdIssuer: '${environment().authentication.loginEndpoint}${entraTenantId}/v2.0'
          clientId: entraClientId
          // decision: app-service__dashboard.identity.entra_client_secret - the name of the app setting
          // that holds the Key Vault reference; the template never contains the secret itself.
          clientSecretSettingName: clientSecretSettingName
        }
        validation: {
          allowedAudiences: ['api://${entraClientId}']
        }
      }
    }
    login: {
      tokenStore: { enabled: false }
    }
    httpSettings: {
      requireHttps: true
    }
  }
}

// ---------------------------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------------------------

resource agent 'Microsoft.Web/sites@2024-11-01' = {
  name: agentAppName
  location: location
  tags: tags
  // decision: app-service__agent.runtime.runtime_stack - container
  kind: 'app,linux,container'

  // decision: app-service__agent.identity.managed_identity - user-assigned, so that AcrPull and the
  // data roles exist before the container first starts.
  // decision: app-service__agent.identity.user_assigned_identity_ids
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${agentIdentityId}': {}
    }
  }

  properties: {
    serverFarmId: plan.id

    // decision: app-service__agent.security.https_only
    httpsOnly: true

    // decision: app-service__agent.networking.public_network_access - nothing outside the VNet calls
    // the agent; without a private endpoint it has no inbound path at all.
    publicNetworkAccess: 'Disabled'

    // decision: app-service__agent.networking.vnet_integration / app-service__agent.networking.integration_subnet
    virtualNetworkSubnetId: integrationSubnetId
    // decision: app-service__agent.networking.vnet_route_all
    outboundVnetRouting: {
      allTraffic: false
    }

    siteConfig: {
      // decision: app-service__agent.runtime.container_image_owner - the image is set here only on
      // the first deployment; later the image pipeline owns it and this keeps what runs.
      linuxFxVersion: !empty(existingAgentLinuxFxVersion) ? existingAgentLinuxFxVersion : 'DOCKER|${registryLoginServer}/${agentContainerImage}'
      // Image pull with the managed identity instead of registry credentials.
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: agentIdentityClientId

      // decision: app-service__agent.runtime.always_on
      alwaysOn: true
      // decision: app-service__agent.runtime.http2_enabled
      http20Enabled: true
      // decision: app-service__agent.security.ftps_state
      ftpsState: 'Disabled'
      // decision: app-service__agent.security.min_tls_version - the Kudu/SCM site gets the same minimum.
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      // decision: app-service__agent.runtime.health_check_path - empty: no healthCheckPath is rendered.

      appSettings: [
        // DefaultAzureCredential needs the client id to pick the user-assigned identity.
        { name: 'AZURE_CLIENT_ID', value: agentIdentityClientId }
        { name: 'PLUGIN_SOURCE', value: pluginSource }
        // See the dashboard: the registry has only a private endpoint.
        { name: 'WEBSITE_PULL_IMAGE_OVER_VNET', value: 'true' }
        { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
        { name: 'STORAGE_ACCOUNT_NAME', value: storageAccountName }
      ]
    }
  }
}

// decision: app-service__agent.security.basic_auth_enabled - two switches, FTP and SCM.
resource agentBasicAuthFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: agent
  name: 'ftp'
  properties: { allow: false }
}

resource agentBasicAuthScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: agent
  name: 'scm'
  properties: { allow: false }
}

// decision: app-service__agent.networking.private_endpoint_subnet - the subnet id is the private
// endpoint subnet 'pe' selected in the network module. The site has one sub-resource, 'sites'.
resource agentPrivateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: agentPrivateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'psc-agent'
        properties: {
          privateLinkServiceId: agent.id
          groupIds: ['sites']
        }
      }
    ]
  }
}

// private_dns_ownership: deployment - this deployment writes the zone group.
resource agentZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = {
  parent: agentPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'azurewebsites', properties: { privateDnsZoneId: privateDnsZoneId } }
    ]
  }
}

// ---------------------------------------------------------------------------------------------
// Drift watcher
// ---------------------------------------------------------------------------------------------

resource drift 'Microsoft.Web/sites@2024-11-01' = {
  name: driftAppName
  location: location
  tags: tags
  // decision: app-service__drift.runtime.runtime_stack - container
  kind: 'app,linux,container'

  // decision: app-service__drift.identity.managed_identity - user-assigned, so that AcrPull and the
  // data roles exist before the container first starts.
  // decision: app-service__drift.identity.user_assigned_identity_ids
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${driftIdentityId}': {}
    }
  }

  properties: {
    serverFarmId: plan.id

    // decision: app-service__drift.security.https_only
    httpsOnly: true

    // decision: app-service__drift.networking.public_network_access - nothing outside the VNet calls
    // the watcher; the dashboard starts a run through its private endpoint.
    publicNetworkAccess: 'Disabled'

    // decision: app-service__drift.networking.vnet_integration / app-service__drift.networking.integration_subnet
    virtualNetworkSubnetId: integrationSubnetId
    // decision: app-service__drift.networking.vnet_route_all - false: the AVM sources are on the
    // internet and there is no NAT gateway; private endpoint addresses still go through the VNet.
    outboundVnetRouting: {
      allTraffic: false
    }

    // Key Vault references are resolved with the user-assigned identity, not the (absent) system one.
    keyVaultReferenceIdentity: driftIdentityId

    siteConfig: {
      // decision: app-service__drift.runtime.container_image_owner - the image is set here only on
      // the first deployment; later the image pipeline owns it and this keeps what runs.
      linuxFxVersion: !empty(existingDriftLinuxFxVersion) ? existingDriftLinuxFxVersion : 'DOCKER|${registryLoginServer}/${driftContainerImage}'
      // Image pull with the managed identity instead of registry credentials.
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: driftIdentityClientId

      // decision: app-service__drift.runtime.always_on - the schedule is a timer inside the app.
      alwaysOn: true
      // decision: app-service__drift.runtime.http2_enabled
      http20Enabled: true
      // decision: app-service__drift.security.ftps_state
      ftpsState: 'Disabled'
      // decision: app-service__drift.security.min_tls_version - the Kudu/SCM site gets the same minimum.
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      // decision: app-service__drift.runtime.health_check_path - empty: no healthCheckPath is rendered.

      appSettings: [
        // DefaultAzureCredential needs the client id to pick the user-assigned identity.
        { name: 'AZURE_CLIENT_ID', value: driftIdentityClientId }
        // See the dashboard: the registry has only a private endpoint.
        { name: 'WEBSITE_PULL_IMAGE_OVER_VNET', value: 'true' }
        { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
        { name: 'STORAGE_ACCOUNT_NAME', value: storageAccountName }
        // The watcher's own GitHub token (contents and pull requests write on this repository only):
        // a Key Vault reference, never a value.
        {
          name: 'GITHUB_TOKEN'
          value: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/${driftGithubTokenSecretName}/)'
        }
        // Comma separated; enforced in the watcher's code only.
        { name: 'AVM_ALLOWED_HOSTS', value: join(driftAllowedHosts, ',') }
        { name: 'DRIFT_SCHEDULE', value: driftSchedule }
      ]
    }
  }
}

// decision: app-service__drift.security.basic_auth_enabled - two switches, FTP and SCM.
resource driftBasicAuthFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: drift
  name: 'ftp'
  properties: { allow: false }
}

resource driftBasicAuthScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: drift
  name: 'scm'
  properties: { allow: false }
}

// decision: app-service__drift.networking.private_endpoint_subnet - the subnet id is the private
// endpoint subnet 'pe' selected in the network module. The site has one sub-resource, 'sites'.
resource driftPrivateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: driftPrivateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'psc-drift'
        properties: {
          privateLinkServiceId: drift.id
          groupIds: ['sites']
        }
      }
    ]
  }
}

// private_dns_ownership: deployment - this deployment writes the zone group.
resource driftZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = {
  parent: driftPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'azurewebsites', properties: { privateDnsZoneId: privateDnsZoneId } }
    ]
  }
}

// ---------------------------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------------------------

resource planDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: plan
  properties: {
    workspaceId: diagnosticWorkspaceId
    // The plan emits metrics only.
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

resource dashboardDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: dashboard
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: app-service__dashboard.observability.diagnostic_categories
    logs: [
      { category: 'AppServiceHTTPLogs', enabled: true }
      { category: 'AppServiceAppLogs', enabled: true }
      { category: 'AppServiceAuditLogs', enabled: true }
      { category: 'AppServiceIPSecAuditLogs', enabled: true }
      { category: 'AppServicePlatformLogs', enabled: true }
    ]
    // decision: app-service__dashboard.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

resource agentDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: agent
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: app-service__agent.observability.diagnostic_categories
    logs: [
      { category: 'AppServiceHTTPLogs', enabled: true }
      { category: 'AppServiceAppLogs', enabled: true }
      { category: 'AppServiceAuditLogs', enabled: true }
      { category: 'AppServiceIPSecAuditLogs', enabled: true }
      { category: 'AppServicePlatformLogs', enabled: true }
    ]
    // decision: app-service__agent.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

resource driftDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: drift
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: app-service__drift.observability.diagnostic_categories
    logs: [
      { category: 'AppServiceHTTPLogs', enabled: true }
      { category: 'AppServiceAppLogs', enabled: true }
      { category: 'AppServiceAuditLogs', enabled: true }
      { category: 'AppServiceIPSecAuditLogs', enabled: true }
      { category: 'AppServicePlatformLogs', enabled: true }
    ]
    // decision: app-service__drift.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output dashboardId string = dashboard.id
output dashboardName string = dashboard.name
output dashboardDefaultHostname string = dashboard.properties.defaultHostName
output agentId string = agent.id
output agentName string = agent.name
output driftId string = drift.id
output driftName string = drift.name
