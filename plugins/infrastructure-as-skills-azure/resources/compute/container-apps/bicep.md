# Rendering Container Apps as Bicep

Mapping from the question set to the environment and the app. General layout, parameters and
naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/container-apps.bicep
```

## With the AVM modules

Two modules, one per ARM resource:

| | Module | Documented against | Resolved |
|---|---|---|---|
| Environment | `br/public:avm/res/app/managed-environment:<version>` | **0.16.0** | 2026-10-23 |
| App | `br/public:avm/res/app/container-app:<version>` | **0.23.0** | 2026-10-23 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact versions.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide and other inputs

| Input | Module | Parameter | Note |
|---|---|---|---|
| (the pull) | app | `registries: [ { server, identity } ]` | `identity` is the user-assigned identity's resource id - never `username`/`passwordSecretRef` |
| `deployment.module_telemetry` | both | `enableTelemetry` | |
| `context.tags` | both | `tags` | |

### The call

```bicep
module environment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'container-apps-environment'
  params: {
    name: environmentName
    location: location
    tags: tags

    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
    // decision: container-apps.environment.zone_redundant - fixed at creation
    zoneRedundant: true
    infrastructureResourceGroupName: infrastructureResourceGroupName
    // decision: container-apps.environment.internal / infrastructure_subnet
    internal: true
    infrastructureSubnetResourceId: infrastructureSubnetId
    publicNetworkAccess: 'Disabled'
    peerTrafficEncryption: true

    // logs through a diagnostic setting, not the workspace's shared key
    appLogsConfiguration: { destination: 'azure-monitor' }
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ContainerAppConsoleLogs' }
          { category: 'ContainerAppSystemLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

module app 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'container-app'
  params: {
    name: appName
    location: location
    tags: tags
    environmentResourceId: environment.outputs.resourceId

    workloadProfileName: 'Consumption'
    activeRevisionsMode: 'Single'

    containers: [
      {
        name: 'app'
        image: containerImage // a tag or digest, never latest
        resources: { cpu: json('0.5'), memory: '1Gi' }
        // decision: container-apps.observability.application_insights
        env: [
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
          { name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING', value: 'Authorization=AAD;ClientId=${identityClientId}' }
        ]
      }
    ]
    scaleSettings: { minReplicas: 2, maxReplicas: 10 }

    // decision: container-apps.ingress.* - the module defaults are external, HTTP, port 80
    ingressExternal: false
    ingressTargetPort: targetPort
    ingressAllowInsecure: false

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    registries: [ { server: registryLoginServer, identity: userAssignedIdentityId } ]
    secrets: [for s in secretReferences: {
      name: s.name
      keyVaultUrl: s.keyVaultSecretUrl
      identity: userAssignedIdentityId
    }]
    enableTelemetry: true
  }
}

output id string = app.outputs.resourceId
output fqdn string = app.outputs.fqdn
```

The members of `containers`, `scaleSettings`, `registries` and `secrets`, and the output
names, are read from the README of the pinned version. The roles on the registry and the vault
are granted before either module is deployed, outside these calls.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).
`application_insights` is matched by the `env` entry's name; its value is the component's
output, an expression in the compiled template.

## Authored rendering

The fallback. `Microsoft.App/managedEnvironments` and `Microsoft.App/containerApps`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Input | Property |
|---|---|
| the pull | `properties.configuration.registries[]: { server, identity }` |
