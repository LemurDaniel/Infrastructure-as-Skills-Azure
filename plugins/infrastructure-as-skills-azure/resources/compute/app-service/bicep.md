# Rendering an App Service as Bicep

Mapping from the question set to the plan and the site. General layout, parameters and
naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/app-service.bicep
```

## With the AVM modules

Two modules, one per ARM resource:

| | Module | Documented against | Resolved |
|---|---|---|---|
| Plan | `br/public:avm/res/web/serverfarm:<version>` | **0.7.0** | 2026-10-18 |
| Site | `br/public:avm/res/web/site:<version>` | **0.24.0** | 2026-10-18 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision → module parameter

| Decision | Module | Parameter | Note |
|---|---|---|---|
| `os_type` | plan | `kind: 'linux'` or `'app'` | `reserved` follows `kind`; the module default is `'app'` (Windows) |
| `os_type` | site | `kind: 'app,linux'` or `'app'` | `'app,linux,container'` for `runtime_stack: container` |
| `sku` | plan | `skuName` | Module default `P1v3` |
| `zone_redundant` | plan | `zoneRedundant` | Module default is **true for `P`/`EP` sizes** - computed, not constant; written |
| `instance_count` | plan | `skuCapacity` | |
| `public_network_access` | site | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | A string; unset, it is disabled only when private endpoints are set |
| `public_network_access` | site | `siteConfig.ipSecurityRestrictionsDefaultAction` | `'Deny'` unless `enabled` |
| `private_endpoint_subnet` | site | `privateEndpoints: [ { subnetResourceId, service: 'sites' } ]` | |
| `deployment.private_dns_records: policy` | site | no `privateDnsZoneGroup` on the endpoint | |
| `vnet_integration`, `integration_subnet` | site | `virtualNetworkSubnetResourceId` | Delegated subnet |
| `vnet_route_all` | site | `outboundVnetRouting: { allTraffic: true }` | |
| `ip_restrictions` | site | `siteConfig.ipSecurityRestrictions` | |
| `managed_identity` | site | `managedIdentities: { systemAssigned: true }` | |
| `https_only` | site | `httpsOnly` | Module default `true`; written |
| `min_tls_version` | site | `siteConfig.minTlsVersion`, `scmMinTlsVersion` | |
| `ftps_state` | site | `siteConfig.ftpsState` | |
| `basic_auth_enabled` | site | `basicPublishingCredentialsPolicies: [ { name: 'ftp', allow: false }, { name: 'scm', allow: false } ]` | |
| `runtime_*` | site | `siteConfig.linuxFxVersion` (`PYTHON\|3.13`) or `windowsFxVersion` | |
| `container_image_owner: image_pipeline` | site | `siteConfig.linuxFxVersion` from a parameter holding the running site's value (read by the pipeline before the deployment), `DOCKER\|<container_image>` while it is empty | Bicep cannot read a property of a resource it deploys; the pipeline reads it |
| `entra_sign_in`, `entra_client_secret` | site | `configs: [ { name: 'authsettingsV2', properties: { ... } } ]` as below, and the app setting holding the Key Vault reference | Parameter shape from the module README of the version pinned |
| `always_on` | site | `siteConfig.alwaysOn` | |
| `health_check_path` | site | `siteConfig.healthCheckPath` | Omitted while empty |
| `http2_enabled` | site | `siteConfig.http20Enabled` | |
| diagnostics | both | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | The plan has metrics only |
| `application_insights` | site | `configs: [ { name: 'appsettings', properties: { APPLICATIONINSIGHTS_CONNECTION_STRING, APPLICATIONINSIGHTS_AUTHENTICATION_STRING } } ]` | The component's `connectionString` output; the second is `Authorization=AAD` (`;ClientId=<client id>` user-assigned) while local auth is off; omitted while empty |
| `deployment.module_telemetry` | both | `enableTelemetry` | |
| `context.tags` | both | `tags` | |

### The call

```bicep
module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'app-service-plan'
  params: {
    name: planName
    location: location
    tags: tags

    kind: 'linux'
    // decision: app-service.hosting.sku
    skuName: skuName
    // decision: app-service.hosting.zone_redundant - computed by the module from the SKU
    zoneRedundant: true
    // decision: app-service.hosting.instance_count - zone redundancy needs two or more
    skuCapacity: 2

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

module app 'br/public:avm/res/web/site:0.24.0' = {
  name: 'app-service'
  params: {
    name: appName
    location: location
    tags: tags

    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId

    // decision: app-service.networking.public_network_access
    publicNetworkAccess: 'Disabled'

    // decision: app-service.networking.vnet_integration / integration_subnet
    virtualNetworkSubnetResourceId: integrationSubnetId
    // decision: app-service.networking.vnet_route_all
    outboundVnetRouting: { allTraffic: true }

    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'sites'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    managedIdentities: { systemAssigned: true }

    httpsOnly: true
    // decision: app-service.security.basic_auth_enabled
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]

    siteConfig: {
      alwaysOn: true
      http20Enabled: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ipSecurityRestrictionsDefaultAction: 'Deny'
      linuxFxVersion: 'PYTHON|3.13'
    }

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'AppServiceHTTPLogs' }
          { category: 'AppServiceAppLogs' }
          { category: 'AppServiceAuditLogs' }
          { category: 'AppServiceIPSecAuditLogs' }
          { category: 'AppServicePlatformLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    // decision: app-service.observability.application_insights
    configs: [
      {
        name: 'appsettings'
        properties: {
          APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsightsConnectionString
          APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'Authorization=AAD'
        }
      }
    ]
    enableTelemetry: true
  }
}

output id string = app.outputs.resourceId
output defaultHostname string = app.outputs.defaultHostname
```

The exact shape of `outboundVnetRouting` and of the `siteConfig` members is read from the
README of the pinned version - the parameter table lists them as object members, and the
spelling above is the ARM property names, which the module passes through.

### A shared plan

With `plan: shared` the instance has **no plan module** and none of `os_type`, `sku`,
`zone_redundant`, `instance_count`: they are the owner's. Its site takes the owner's plan id:

```bicep
module webMcp 'br/public:avm/res/web/site:0.24.0' = {
  name: 'web-mcp'
  params: {
    // decision: app-service__mcp.hosting.plan - shared with app-service__web
    serverFarmResourceId: plan.outputs.resourceId
    // ... the site's own decisions, as above; virtualNetworkSubnetResourceId is the owner's
  }
}
```

The private endpoint and the `privatelink.azurewebsites.net` record are per app; the zone is already
in `wiring.private_dns_zones` ([private-dns-zones.md](../../../core/iac-rendering/references/private-dns-zones.md)).

### Deployment slots

`slots` is an array on the site call. **A Bicep slot inherits most of the site** -
`siteConfig`, `managedIdentities`, `virtualNetworkSubnetResourceId`, `outboundVnetRouting`,
`basicPublishingCredentialsPolicies`, `httpsOnly`, `lock`, `configs` - but not its
`privateEndpoints` (default `[]`) or its `diagnosticSettings`, and `publicNetworkAccess`
falls back to `Disabled` only when the slot or the site has a private endpoint. Write
`privateEndpoints`, `diagnosticSettings` and `publicNetworkAccess` on each slot; leave the
inherited ones inherited so that the slot cannot drift from the site. Checked against
0.24.0 (2026-10-27).

| Decision | Parameter | Note |
|---|---|---|
| `deployment_slots` | `slots: [ { name: '<name>', ... } ]` | Premium v3 plan |
| `slot_access: same_as_app` / `private` | `slots[].privateEndpoints: [ { service: 'sites-<name>', subnetResourceId } ]` | The slot's own private link group |
| `slot_access: same_as_app` (waf) | an origin group and route of the slot on the Front Door call, over private link to `sites-<name>` | |
| `slot_access: known_addresses`, `slot_ip_restrictions` | `slots[].publicNetworkAccess: 'Enabled'`, `slots[].siteConfig` with `ipSecurityRestrictions`, `ipSecurityRestrictionsDefaultAction: 'Deny'`, `scmIpSecurityRestrictionsUseMain: true` | A slot `siteConfig` **replaces** the site's: write the whole object |
| `managed_identity` (forced `user_assigned`) | `managedIdentities: { userAssignedResourceIds: [...] }` on the site | Inherited by the slot |
| `auto_swap` | `slots[].siteConfig.autoSwapSlotName: 'production'` | Omitted while `false`; needs the whole `siteConfig` on the slot |
| `sticky_settings` | `configs: [ { name: 'slotConfigNames', properties: { appSettingNames: [...] } } ]` on the site | **Write `configs` on each slot** - the slot inherits the site's `configs`, and `slotConfigNames` is not available for slots: the slot's list holds its `appsettings` only (`[]` when it has none) |
| `application_insights` | `slots[].configs: [ { name: 'appsettings', properties: { APPLICATIONINSIGHTS_CONNECTION_STRING, APPLICATIONINSIGHTS_AUTHENTICATION_STRING } } ]` | The same component as the site |
| diagnostics | `slots[].diagnosticSettings` | Same categories as the site |

```bicep
    // decision: app-service.slots.deployment_slots
    slots: [
      {
        name: 'test'
        // decision: app-service.slots.slot_access - same_as_app behind the entry
        publicNetworkAccess: 'Disabled'
        privateEndpoints: [
          {
            name: slotPrivateEndpointName
            service: 'sites-test'
            subnetResourceId: privateEndpointSubnetId
          }
        ]
        // the site's slotConfigNames must not reach the slot; its app settings are its own
        configs: [
          {
            name: 'appsettings'
            properties: {
              APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsightsConnectionString
              APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'Authorization=AAD'
            }
          }
        ]
        diagnosticSettings: [
          {
            workspaceResourceId: diagnosticWorkspaceId
            logCategoriesAndGroups: [
              { category: 'AppServiceHTTPLogs' }
              { category: 'AppServiceAppLogs' }
              { category: 'AppServiceAuditLogs' }
              { category: 'AppServiceIPSecAuditLogs' }
              { category: 'AppServicePlatformLogs' }
            ]
            metricCategories: [ { category: 'AllMetrics' } ]
          }
        ]
      }
    ]
```

`slots` compiles into the site's nested deployment as one parameter, so every slot
decision is observable in `tests/*.armtest.yaml` as a member of `slots.value[<i>]`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value`
is the decision ([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)),
so every decision above is observable in `tests/*.armtest.yaml` - including the plan's,
which the Terraform side cannot see. `siteConfig` is one object parameter; its members
are matched inside it. `application_insights` is the `APPLICATIONINSIGHTS_CONNECTION_STRING`
key of the `appsettings` entry in `configs`; its value is the component's output, an
expression in the compiled template, so the test matches the key, not the value.

## Authored rendering

The fallback - `implementation: authored`, a repository that already renders the app this
way, or reading what the modules do inside.

| Decision | Property |
|---|---|
| `os_type` | `Microsoft.Web/serverfarms` `kind` and `properties.reserved` |
| `sku` | `sku.name` on the plan |
| `zone_redundant` | `properties.zoneRedundant` on the plan |
| `instance_count` | `sku.capacity` on the plan |
| `public_network_access` | `properties.publicNetworkAccess` on the site |
| `vnet_integration` | `properties.virtualNetworkSubnetId` |
| `vnet_route_all` | `properties.vnetRouteAllEnabled` (older) / `outboundVnetRouting.allTraffic` |
| `https_only` | `properties.httpsOnly` |
| `min_tls_version` | `properties.siteConfig.minTlsVersion` |
| `basic_auth_enabled` | child resources `basicPublishingCredentialsPolicies/ftp` and `/scm`, `properties.allow` |
| `container_image_owner: image_pipeline` | `properties.siteConfig.linuxFxVersion` from a parameter with the running value, the bootstrap image while it is empty |
| `entra_sign_in`, `entra_client_secret` | child `Microsoft.Web/sites/config` `authsettingsV2`: `globalValidation { requireAuthentication: true, unauthenticatedClientAction: 'RedirectToLoginPage' }`, `identityProviders.azureActiveDirectory.registration { openIdIssuer, clientId, clientSecretSettingName }` |

```bicep
resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'linux'
  sku: { name: skuName, capacity: 2 }
  properties: {
    reserved: true
    zoneRedundant: true
  }
}
```

The authored site carries the same members as the module call above under `properties`.
Basic authentication is two child resources, not a property of the site - the part
authored renders forget.
