# Rendering a Function App as Bicep

Mapping from the question set to the plan and the site. General layout, parameters and naming
are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
The two modules are the ones of the [App Service](../app-service/bicep.md) reference; read it
first, only what differs is here.

```bash
bicep build --stdout modules/function-app.bicep
```

## With the AVM modules

| | Module | Documented against | Resolved |
|---|---|---|---|
| Plan | `br/public:avm/res/web/serverfarm:<version>` | **0.7.0** | 2026-10-23 |
| Site | `br/public:avm/res/web/site:<version>` | **0.24.0** | 2026-10-23 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Module | Parameter | Note |
|---|---|---|---|
| `plan_type` | plan | `skuName: 'FC1'` / `'EP1'`..`'EP3'`, `kind: 'linux'` | Flex is Linux only; `reserved` follows `kind` |
| `plan_type` | site | `kind: 'functionapp,linux'` | |
| `runtime_stack`, `runtime_version` | site | `functionAppConfig.runtime: { name, version }` (Flex); `siteConfig.linuxFxVersion` (Premium) | |
| `zone_redundant` | plan | `zoneRedundant` | Computed by the module from the SKU; written |
| `max_instance_count`, `always_ready_instances`, `instance_memory_mb` | site | `functionAppConfig.scaleAndConcurrency: { maximumInstanceCount, instanceMemoryMB, alwaysReady: [ { name: 'http', instanceCount } ] }` | Flex |
| `host_storage_account`, `host_storage_auth` | site | `configs: [ { name: 'appsettings', properties: { AzureWebJobsStorage__accountName, AzureWebJobsStorage__credential: 'managedidentity', AzureWebJobsStorage__clientId } } ]` | The host connection; **never** `AzureWebJobsStorage` with a key |
| `host_storage_auth`, `deployment_container` | site | `functionAppConfig.deployment.storage: { type: 'blobContainer', value, authentication: { type: 'UserAssignedIdentity', userAssignedIdentityResourceId } }` | The second connection, Flex only |
| `public_network_access` | site | `publicNetworkAccess`, `siteConfig.ipSecurityRestrictionsDefaultAction` | |
| `private_endpoint_subnet` | site | `privateEndpoints: [ { subnetResourceId, service: 'sites' } ]` | |
| `vnet_integration`, `integration_subnet`, `vnet_route_all` | site | `virtualNetworkSubnetResourceId`, `outboundVnetRouting: { allTraffic }` | Delegation per plan |
| `managed_identity` | site | `managedIdentities: { userAssignedResourceIds }`, `keyVaultAccessIdentityResourceId` | |
| `https_only`, `min_tls_version` | site | `httpsOnly`, `siteConfig.minTlsVersion`, `scmMinTlsVersion` | |
| `basic_auth_enabled` | site | `basicPublishingCredentialsPolicies: [ { name: 'ftp', allow: false }, { name: 'scm', allow: false } ]` | |
| `application_insights` | site | the `APPLICATIONINSIGHTS_CONNECTION_STRING` setting through `configs`, and `APPLICATIONINSIGHTS_AUTHENTICATION_STRING` (`Authorization=AAD`, `;ClientId=<client id>` user-assigned) while local auth is off | Omitted while empty |
| `diagnostic_*`, `metrics_enabled` | both | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups, metricCategories } ]` | The plan has metrics only |
| `deployment.module_telemetry` | both | `enableTelemetry` | |
| `context.tags` | both | `tags` | |

### The call

```bicep
module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'function-plan'
  params: {
    name: planName
    location: location
    tags: tags
    kind: 'linux'
    skuName: 'FC1' // decision: function-app.hosting.plan_type
    zoneRedundant: true
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

module function 'br/public:avm/res/web/site:0.24.0' = {
  name: 'function-app'
  params: {
    name: functionName
    location: location
    tags: tags
    kind: 'functionapp,linux'
    serverFarmResourceId: plan.outputs.resourceId

    // decision: function-app.hosting.* and function-app.storage.* (Flex)
    functionAppConfig: {
      runtime: { name: 'python', version: '3.12' }
      scaleAndConcurrency: {
        maximumInstanceCount: 20
        instanceMemoryMB: 2048
        alwaysReady: [ { name: 'http', instanceCount: 1 } ]
      }
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${hostStorageBlobEndpoint}${deploymentContainer}'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: userAssignedIdentityId
          }
        }
      }
    }
    // the host's own storage connection - identity, never the key
    configs: [
      {
        name: 'appsettings'
        properties: {
          AzureWebJobsStorage__accountName: hostStorageAccountName
          AzureWebJobsStorage__credential: 'managedidentity'
          AzureWebJobsStorage__clientId: identityClientId
        }
      }
    ]

    // decision: function-app.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    virtualNetworkSubnetResourceId: integrationSubnetId
    outboundVnetRouting: { allTraffic: true }
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'sites'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    keyVaultAccessIdentityResourceId: userAssignedIdentityId

    httpsOnly: true
    // decision: function-app.security.basic_auth_enabled
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
    siteConfig: {
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ipSecurityRestrictionsDefaultAction: 'Deny'
    }

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'FunctionAppLogs' }
          { category: 'AppServiceAuditLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = function.outputs.resourceId
output defaultHostname string = function.outputs.defaultHostname
```

The members of `functionAppConfig` and `configs`, and the Premium form (no `functionAppConfig`,
`siteConfig.linuxFxVersion` and `alwaysOn` instead), are read from the README of the pinned
version. The roles on the host storage account are granted before the site is deployed,
outside these calls.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)) - including the
plan's, which the Terraform side cannot see. `functionAppConfig` is one object parameter; its
members are matched inside it.

## Authored rendering

The fallback. `Microsoft.Web/serverfarms` (`sku.name: 'FC1'`, `reserved: true`) and
`Microsoft.Web/sites` with `kind: 'functionapp,linux'` and `properties.functionAppConfig`
(`runtime`, `scaleAndConcurrency`, `deployment.storage`); basic authentication is two child
resources, not a property of the site, as for the App Service.
