// Module "app" (spec composition: app) - Linux App Service plan and the container web app with
// Entra sign-in (authsettingsV2), VNet integration and diagnostics.
// Needs: network (integration subnet), observability (workspace), identity (user-assigned),
// registry (login server), vault (vault URI for the client secret reference).

@description('Finished plan name, assembled in main.bicep.')
param planName string

@description('Finished app name, assembled in main.bicep. It is the public hostname.')
param appName string

@description('Azure region.')
param location string

@description('Tags applied to every resource of the module.')
param tags object

@description('Resource id of the delegated integration subnet (network module output).')
param integrationSubnetId string

@description('Resource id of the Log Analytics workspace (observability module output).')
param diagnosticWorkspaceId string

@description('Resource id of the user-assigned identity (identity module output).')
param identityId string

@description('Client id of the user-assigned identity (identity module output).')
param identityClientId string

@description('Login server of the container registry (registry module output).')
param registryLoginServer string

@description('Vault URI (vault module output); the client secret is read from there through a Key Vault reference.')
param vaultUri string

@description('Endpoint of the Foundry account (ai module output); the agent calls the models there.')
param foundryEndpoint string

@description('Name of the storage account (storage module output); the app reads and writes eval results there.')
param storageAccountName string

@description('Bootstrap image as name:tag, without the registry; used only while the web app has no image yet. After that the image belongs to the separate image pipeline (no latest).')
param containerImage string

@description('linuxFxVersion the web app runs now (DOCKER|<registry>/<name>:<tag>), read by the pipeline before the deployment; empty on the first deployment. Kept as is so this template never rolls the image back.')
param existingLinuxFxVersion string = ''

@description('Where the agent fetches the Claude plugin from (OPEN in the stage file).')
param pluginSource string

@description('Client id of the existing Entra app registration used for sign-in (stage file).')
param entraClientId string

@description('Tenant id of the Entra tenant that signs users in (stage file).')
param entraTenantId string

// decision: key-vault.security.secret_placeholders - the name of the secret the app reads.
var clientSecretName = 'entra-client-secret'
var clientSecretSettingName = 'MICROSOFT_PROVIDER_AUTHENTICATION_SECRET'

resource plan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: planName
  location: location
  tags: tags
  // decision: app-service.hosting.os_type
  kind: 'linux'
  sku: {
    // decision: app-service.hosting.sku
    name: 'B2'
    // decision: app-service.hosting.instance_count
    capacity: 1
  }
  properties: {
    // decision: app-service.hosting.os_type - reserved is what makes the plan Linux.
    reserved: true
    // decision: app-service.hosting.zone_redundant
    zoneRedundant: false
  }
}

resource site 'Microsoft.Web/sites@2024-11-01' = {
  name: appName
  location: location
  tags: tags
  // decision: app-service.runtime.runtime_stack - container
  kind: 'app,linux,container'

  // decision: app-service.identity.managed_identity - user-assigned, so that AcrPull and the data
  // roles exist before the container first starts.
  // decision: app-service.identity.user_assigned_identity_ids
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }

  properties: {
    serverFarmId: plan.id

    // decision: app-service.security.https_only
    httpsOnly: true

    // decision: app-service.networking.public_network_access - the dashboard is internet-facing.
    publicNetworkAccess: 'Enabled'

    // decision: app-service.networking.vnet_integration / app-service.networking.integration_subnet
    virtualNetworkSubnetId: integrationSubnetId
    // decision: app-service.networking.vnet_route_all
    outboundVnetRouting: {
      allTraffic: false
    }

    // Key Vault references are resolved with the user-assigned identity, not the (absent) system one.
    keyVaultReferenceIdentity: identityId

    siteConfig: {
      // decision: app-service.runtime.container_image_owner - the image is set here only on the
      // first deployment; later the image pipeline owns it and this keeps what runs.
      linuxFxVersion: !empty(existingLinuxFxVersion) ? existingLinuxFxVersion : 'DOCKER|${registryLoginServer}/${containerImage}'
      // Image pull with the managed identity instead of registry credentials.
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: identityClientId

      // decision: app-service.runtime.always_on
      alwaysOn: true
      // decision: app-service.runtime.http2_enabled
      http20Enabled: true
      // decision: app-service.security.ftps_state
      ftpsState: 'Disabled'
      // decision: app-service.security.min_tls_version - the Kudu/SCM site gets the same minimum.
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      // decision: app-service.runtime.health_check_path - empty: no healthCheckPath is rendered
      // (a path that does not return 2xx would mark the whole plan unhealthy).

      appSettings: [
        // The sign-in's client secret: a Key Vault reference, never a value.
        {
          name: clientSecretSettingName
          value: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/${clientSecretName}/)'
        }
        // DefaultAzureCredential needs the client id to pick the user-assigned identity.
        { name: 'AZURE_CLIENT_ID', value: identityClientId }
        { name: 'PLUGIN_SOURCE', value: pluginSource }
        // The registry is reachable only through its private endpoint, so the platform's image pull
        // must go through the VNet integration. The site property vnetImagePullEnabled is not in the
        // type definition of API 2024-11-01 (bicep build rejects it), hence the app setting.
        { name: 'WEBSITE_PULL_IMAGE_OVER_VNET', value: 'true' }
        { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
        { name: 'STORAGE_ACCOUNT_NAME', value: storageAccountName }
      ]
    }
  }
}

// decision: app-service.security.basic_auth_enabled - two switches, FTP and SCM.
resource basicAuthFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: site
  name: 'ftp'
  properties: { allow: false }
}

resource basicAuthScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: site
  name: 'scm'
  properties: { allow: false }
}

// Hand-rendered (no question set): sign-in with the existing Entra app registration. Anonymous
// requests are redirected to the login. The redirect URI
// https://<app host>/.auth/login/aad/callback is registered by the identity team after the first
// deployment (spec open: resources.app-service.identity.entra_sign_in).
// decision: app-service.identity.entra_sign_in
resource authSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  parent: site
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
          // decision: app-service.identity.entra_client_secret - the name of the app setting that
          // holds the Key Vault reference; the template never contains the secret itself.
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

resource siteDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: site
  properties: {
    workspaceId: diagnosticWorkspaceId
    // decision: app-service.observability.diagnostic_categories
    logs: [
      { category: 'AppServiceHTTPLogs', enabled: true }
      { category: 'AppServiceAppLogs', enabled: true }
      { category: 'AppServiceAuditLogs', enabled: true }
      { category: 'AppServiceIPSecAuditLogs', enabled: true }
      { category: 'AppServicePlatformLogs', enabled: true }
    ]
    // decision: app-service.observability.metrics_enabled
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output id string = site.id
output name string = site.name
output defaultHostname string = site.properties.defaultHostName
