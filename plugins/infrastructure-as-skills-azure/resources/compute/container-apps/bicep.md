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

| Decision | Module | Parameter | Note |
|---|---|---|---|
| `workload_profile` | env | `workloadProfiles: [ { name, workloadProfileType } ]` | **Required when `zoneRedundant` is true** (the README: WAF compliance) |
| `workload_profile` | app | `workloadProfileName` | |
| `zone_redundant` | env | `zoneRedundant` | Default `true`; written. Also needs `infrastructureResourceGroupName` per the README |
| `internal`, `infrastructure_subnet` | env | `internal`, `infrastructureSubnetResourceId` | `internal` default `false`; the subnet is required with it |
| `public_network_access` | env | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Default `'Disabled'`; written |
| `peer_traffic_encryption` | env | `peerTrafficEncryption` | Default `true`; written |
| `diagnostic_workspace` | env | `appLogsConfiguration: { destination: 'azure-monitor' }` | Not `log-analytics` (shared key) |
| `diagnostic_*`, `metrics_enabled` | env | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `container_image`, `container_size` | app | `containers: [ { name, image, resources: { cpu, memory } } ]` | `cpu` is a `json('0.5')` |
| `application_insights` | app | `containers[].env: [ { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value }, { name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING', value: 'Authorization=AAD;ClientId=<client id>' } ]` | The second while local auth is off, with the app's user-assigned identity; omitted while empty |
| `min_replicas`, `max_replicas` | app | `scaleSettings: { minReplicas, maxReplicas }` | |
| `revision_mode` | app | `activeRevisionsMode` | Default `'Single'`; written |
| `ingress` | app | `disableIngress` (for `none`), `ingressExternal` | **`ingressExternal` defaults to `true`**; written |
| `target_port` | app | `ingressTargetPort` | **Default 80**; written |
| `allow_insecure` | app | `ingressAllowInsecure` | **Default `true`**; written |
| `managed_identity` | app | `managedIdentities: { userAssignedResourceIds }` | |
| (the pull) | app | `registries: [ { server, identity } ]` | `identity` is the user-assigned identity's resource id - never `username`/`passwordSecretRef` |
| `secret_references` | app | `secrets: [ { name, keyVaultUrl, identity } ]` | Never `value` |
| `role_assignments` | app | `roleAssignments` | |
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
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).
`application_insights` is matched by the `env` entry's name; its value is the component's
output, an expression in the compiled template.

## Authored rendering

The fallback. `Microsoft.App/managedEnvironments` and `Microsoft.App/containerApps`:

| Decision | Property |
|---|---|
| `zone_redundant` | `properties.zoneRedundant` on the environment |
| `internal`, `infrastructure_subnet` | `properties.vnetConfiguration: { internal, infrastructureSubnetId }` |
| `public_network_access` | `properties.publicNetworkAccess` on the environment |
| `peer_traffic_encryption` | `properties.peerTrafficConfiguration.encryption.enabled` |
| `workload_profile` | `properties.workloadProfiles[]` on the environment, `properties.workloadProfileName` on the app |
| `diagnostic_workspace` | `properties.appLogsConfiguration.destination: 'azure-monitor'` |
| ingress | `properties.configuration.ingress: { external, targetPort, allowInsecure }` |
| the pull | `properties.configuration.registries[]: { server, identity }` |
| `secret_references` | `properties.configuration.secrets[]: { name, keyVaultUrl, identity }` |
