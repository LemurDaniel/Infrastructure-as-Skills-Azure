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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module | Parameter | Note |
|---|---|---|---|
| `deployment.private_dns_records: policy` | site | no `privateDnsZoneGroup` on the endpoint | |
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

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

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
so every decision in render-map.yaml is observable in `tests/*.armtest.yaml` - including the plan's,
which the Terraform side cannot see. `siteConfig` is one object parameter; its members
are matched inside it. `application_insights` is the `APPLICATIONINSIGHTS_CONNECTION_STRING`
key of the `appsettings` entry in `configs`; its value is the component's output, an
expression in the compiled template, so the test matches the key, not the value.

## Authored rendering

The fallback - `implementation: authored`, a repository that already renders the app this
way, or reading what the modules do inside.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

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
