# Rendering Logic Apps as Bicep

Mapping from the question set to the resources. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
`hosting` picks the modules: Standard is the plan and site modules of the
[App Service](../../compute/app-service/bicep.md) and [Function App](../../compute/function-app/bicep.md)
references with the workflow kind; Consumption is the workflow module.

```bash
bicep build --stdout modules/logic-app.bicep
```

## With the AVM modules

| | Module | Documented against | Resolved |
|---|---|---|---|
| Standard plan | `br/public:avm/res/web/serverfarm:<version>` | **0.7.0** | 2026-10-26 |
| Standard site | `br/public:avm/res/web/site:<version>` | **0.24.0** | 2026-10-26 |
| Consumption workflow | `br/public:avm/res/logic/workflow:<version>` | **0.6.0** | 2026-10-26 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Module | Parameter | Note |
|---|---|---|---|
| `hosting: standard` | site | `kind: 'functionapp,workflowapp'` | **Required**; `'functionapp,workflowapp,linux'` for a Linux plan |
| `hosting: consumption` | workflow | the module itself | One module per `workflows` entry |
| `plan: shared`, `shared_plan_with` | site | `serverFarmResourceId` = the owner's plan id; no plan module | |
| `plan_sku` | plan | `skuName: 'WS1'`, `kind: 'elastic'` | `reserved` follows `kind`; Windows |
| `zone_redundant` | plan | `zoneRedundant` | Computed by the module from the SKU when unset; written |
| `instance_count` | plan | `skuCapacity` | |
| `max_instance_count` | plan | `maximumElasticWorkerCount` | |
| `workflows` | site | - (content) | Standard: `not_testable` |
| `state` | workflow | `state` | Default `'Enabled'`; written |
| `trigger_authentication` | workflow | `triggersAccessControlConfiguration: { allowedCallerIpAddresses, openAuthenticationPolicies }` | ARM spelling; the SAS switch's property is checked before a render |
| `trigger_authentication` | site | `configs: [ { name: 'authsettingsV2', ... } ]` | Easy Auth in front of the request triggers |
| `host_storage_account`, `host_storage_auth` | site | `configs: [ { name: 'appsettings', properties: { AzureWebJobsStorage__accountName, AzureWebJobsStorage__credential: 'managedidentity', AzureWebJobsStorage__clientId, WEBSITE_CONTENTAZUREFILECONNECTIONSTRING: <Key Vault reference>, WEBSITE_CONTENTSHARE } } ]` | The module writes no logic-app settings of its own; **every host setting is written here**, including `FUNCTIONS_EXTENSION_VERSION`, `FUNCTIONS_WORKER_RUNTIME: 'dotnet'`, `WEBSITE_NODE_DEFAULT_VERSION` and the workflow extension bundle - the list is in the call |
| `public_network_access` | site | `publicNetworkAccess`, `siteConfig.ipSecurityRestrictionsDefaultAction` | Unset, disabled only with private endpoints; written |
| `public_network_access` | workflow | `triggersAccessControlConfiguration.allowedCallerIpAddresses` | No `Disabled` exists |
| `allowed_caller_ip_ranges` | site / workflow | `siteConfig.ipSecurityRestrictions` / `allowedCallerIpAddresses[].addressRange` | |
| `private_endpoint_subnet` | site | `privateEndpoints: [ { service: 'sites', subnetResourceId } ]` | |
| `deployment.private_dns_records: policy` | site | no `privateDnsZoneGroup` on the endpoint | |
| `vnet_integration`, `integration_subnet`, `vnet_route_all` | site | `virtualNetworkSubnetResourceId`, `outboundVnetRouting: { allTraffic }` | |
| `managed_identity`, `user_assigned_identity_ids` | site / workflow | `managedIdentities: { userAssignedResourceIds }`, site also `keyVaultAccessIdentityResourceId` | |
| `role_assignments` | site / workflow | `roleAssignments` | |
| `https_only` | site | `httpsOnly` | Default `true`; written |
| `min_tls_version` | site | `siteConfig.minTlsVersion`, `scmMinTlsVersion` | |
| `basic_auth_enabled` | site | `basicPublishingCredentialsPolicies: [ { name: 'ftp', allow: false }, { name: 'scm', allow: false } ]` | |
| `application_insights` | site | `APPLICATIONINSIGHTS_CONNECTION_STRING` in the `appsettings` config | Omitted while empty |
| `diagnostic_*`, `metrics_enabled` | all | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | The plan has metrics only |
| `deployment.module_telemetry` | all | `enableTelemetry` | |
| `context.tags` | all | `tags` | |

### The call - Standard

```bicep
module logicPlan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'logic-plan'
  params: {
    name: logicPlanName
    location: location
    tags: tags
    kind: 'elastic'
    skuName: 'WS1' // decision: logic-app.hosting.plan_sku
    // decision: logic-app.hosting.instance_count, max_instance_count, zone_redundant
    skuCapacity: 2
    maximumElasticWorkerCount: 20
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

module logicApp 'br/public:avm/res/web/site:0.24.0' = {
  name: 'logic-app'
  params: {
    name: logicAppName
    location: location
    tags: tags
    kind: 'functionapp,workflowapp' // decision: logic-app.hosting.hosting
    serverFarmResourceId: logicPlan.outputs.resourceId

    // decision: logic-app.storage.host_storage_account, host_storage_auth - the host settings;
    // identity for blob, queue and table, a Key Vault reference for the content share
    configs: [
      {
        name: 'appsettings'
        properties: {
          FUNCTIONS_EXTENSION_VERSION: '~4'
          FUNCTIONS_WORKER_RUNTIME: 'dotnet'
          WEBSITE_NODE_DEFAULT_VERSION: '~22'
          AzureFunctionsJobHost__extensionBundle__id: 'Microsoft.Azure.Functions.ExtensionBundle.Workflows'
          AzureFunctionsJobHost__extensionBundle__version: '[1.*, 2.0.0)'
          AzureWebJobsStorage__accountName: hostStorageAccountName
          AzureWebJobsStorage__credential: 'managedidentity'
          AzureWebJobsStorage__clientId: identityClientId
          WEBSITE_CONTENTAZUREFILECONNECTIONSTRING: contentShareConnectionKvReference
          WEBSITE_CONTENTSHARE: logicAppName
          APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsightsConnectionString
        }
      }
    ]

    // decision: logic-app.networking.public_network_access
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
    // decision: logic-app.security.basic_auth_enabled
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
    siteConfig: {
      minTlsVersion: '1.2' // decision: logic-app.security.min_tls_version
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      ipSecurityRestrictionsDefaultAction: 'Deny'
      scmIpSecurityRestrictionsUseMain: true
      netFrameworkVersion: 'v8.0'
    }

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [ { category: 'WorkflowRuntime' } ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = logicApp.outputs.resourceId
```

`contentShareConnectionKvReference` is `'@Microsoft.KeyVault(SecretUri=${secretUri})'` for a secret
holding the storage account's connection string, read through `keyVaultAccessIdentityResourceId`.
The extension-bundle id and version range, the runtime version and the Node version are the
platform's current values for a Standard logic app and are read from the Logic Apps Standard
app-settings reference before a render, not recalled.

### The call - Consumption

```bicep
module workflow 'br/public:avm/res/logic/workflow:0.6.0' = [for wf in workflows: {
  name: 'workflow-${wf}'
  params: {
    name: '${logicAppName}-${wf}'
    location: location
    tags: tags
    state: 'Enabled' // decision: logic-app.workflows.state
    // decision: logic-app.workflows.trigger_authentication - Entra tokens, no SAS
    triggersAccessControlConfiguration: {
      allowedCallerIpAddresses: []
      openAuthenticationPolicies: {
        policies: {
          callers: {
            type: 'AAD'
            claims: [ { name: 'aud', value: 'https://management.core.windows.net/' } ]
          }
        }
      }
    }
    workflowTriggers: {}
    workflowActions: {}
    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [ { category: 'WorkflowRuntime' } ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}]
```

`workflowTriggers` and `workflowActions` stay empty: the definition is content deployed by the
integration team over this resource. The `aud` claim is the audience the callers' tokens carry;
a bot or application audience replaces the management one.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the Consumption
loop compiles to a `copy`, so its decisions are matched on the expression text. `workflows` on
Standard is `not_testable` (content).

## Authored rendering

The fallback. `Microsoft.Web/serverFarms` (`sku: { name: 'WS1', capacity }`, `kind: 'elastic'`,
`properties.zoneRedundant`, `maximumElasticWorkerCount`), `Microsoft.Web/sites` with
`kind: 'functionapp,workflowapp'` and `properties`:

| Decision | Property |
|---|---|
| `host_storage_*`, `application_insights` | child `config/appsettings` with the settings above |
| `public_network_access`, `allowed_caller_ip_ranges` | `properties.publicNetworkAccess`, `siteConfig.ipSecurityRestrictions`, `ipSecurityRestrictionsDefaultAction` |
| `vnet_integration`, `vnet_route_all` | `properties.virtualNetworkSubnetId`, `vnetRouteAllEnabled` |
| `managed_identity` | `identity` (top level), `properties.keyVaultReferenceIdentity` |
| `https_only`, `min_tls_version` | `properties.httpsOnly`, `siteConfig.minTlsVersion`, `scmMinTlsVersion` |
| `basic_auth_enabled` | children `basicPublishingCredentialsPolicies/ftp` and `/scm` with `allow: false` |
| `private_endpoint_subnet` | `Microsoft.Network/privateEndpoints` with `groupIds: [ 'sites' ]` |
| Consumption | `Microsoft.Logic/workflows` with `properties.state`, `accessControl.triggers`, `definition`, `identity` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` scoped to each resource |
