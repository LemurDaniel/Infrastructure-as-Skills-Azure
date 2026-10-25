# Rendering Container Instances as Bicep

Mapping from the question set to the container group. General layout, parameters and naming are
in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/container-instances.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/container-instance/container-group:<version>` | **0.7.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `container_image`, `cpu`, `memory_in_gb`, `exposed_ports` | `containers: [ { name, properties: { image, ports, resources: { requests: { cpu, memoryInGB } } } } ]` | `cpu` an integer, `memoryInGB` a **string** |
| `restart_policy` | `restartPolicy` | Default **`'Always'`**; written |
| `availability_zone` | `availabilityZone` | **Required**; `-1` for `none`, else `1`, `2`, `3` |
| `ip_address_type` | `ipAddress: { type: 'Private' / 'Public', ports }` | The module sends `Public` when `ipAddress` is given without a type; written |
| `subnet_id` | `subnets: [ { subnetResourceId } ]` | |
| `exposed_ports` | `ipAddress.ports: [ { port, protocol } ]` and the container's `ports` | Both lists must agree |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | |
| `registry_login_server` | `imageRegistryCredentials: [ { server, identity } ]` | `identity` is the identity's resource id - never `username` / `password` |
| `key_management`, `cmk_key_vault_key_id` | `customerManagedKey: { keyVaultResourceId, keyName, userAssignedIdentityResourceId }` | The module resolves the current key version at deployment (rotation unsupported by the service) |
| `diagnostic_workspace`, `log_type` | `logAnalytics: { workspaceResourceId, logType }` | `'ContainerInstanceLogs'` or `'ContainerInsights'`; the module reads the shared key itself |
| `role_assignments` | none | **No parameter**: a `Microsoft.Authorization/roleAssignments` resource beside the module, scoped to the group |
| `deployment.resource_lock` | none | Compute carries no lock |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module group 'br/public:avm/res/container-instance/container-group:0.7.1' = {
  name: 'container-group'
  params: {
    name: groupName
    location: location
    tags: tags

    // decision: container-instances.container_group.availability_zone - required, -1 is none
    availabilityZone: -1
    osType: 'Linux'
    // decision: container-instances.container_group.restart_policy - the module default is Always
    restartPolicy: 'OnFailure'
    containers: [
      {
        name: 'main'
        properties: {
          image: containerImage // a tag or digest, never latest
          ports: []
          resources: {
            requests: {
              cpu: 1
              memoryInGB: '2'
            }
          }
        }
      }
    ]

    // decision: container-instances.networking.ip_address_type - injected into a delegated subnet
    ipAddress: {
      type: 'Private'
      ports: []
    }
    subnets: [ { subnetResourceId: subnetId } ]

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    imageRegistryCredentials: [
      {
        server: registryLoginServer
        identity: userAssignedIdentityId
      }
    ]

    // decision: container-instances.security.key_management - only for customer_managed
    customerManagedKey: {
      keyVaultResourceId: keyVaultResourceId
      keyName: keyName
      userAssignedIdentityResourceId: userAssignedIdentityId
    }

    logAnalytics: {
      logType: 'ContainerInstanceLogs'
      workspaceResourceId: diagnosticWorkspaceId
    }
    enableTelemetry: true
  }
}

// the module has no role assignment parameter: written beside it, scoped to the group
resource groupRef 'Microsoft.ContainerInstance/containerGroups@2025-09-01' existing = {
  name: groupName
  dependsOn: [ group ]
}

resource assignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (ra, i) in roleAssignments: {
  name: guid(groupRef.id, ra.principalId, ra.roleDefinitionId)
  scope: groupRef
  properties: {
    roleDefinitionId: ra.roleDefinitionId
    principalId: ra.principalId
    principalType: ra.?principalType ?? 'ServicePrincipal'
  }
}]

output id string = group.outputs.resourceId
output ipAddress string? = group.outputs.?iPv4Address
```

For `public`, `ipAddress.type` is `'Public'` and `subnets` is omitted. Omit `customerManagedKey`
for `platform_managed` and `imageRegistryCredentials` for a public image. The call compiles with
`bicep build` against 0.7.1 (including the role assignment resource, which takes the role
definition id, not a name). The member names are read from the README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the role
assignment is a plain resource and is asserted on its own entry.

## Authored rendering

The fallback. `Microsoft.ContainerInstance/containerGroups` with `identity` and `properties`:

| Decision | Property |
|---|---|
| `container_image`, `cpu`, `memory_in_gb`, `exposed_ports` | `properties.containers[].properties: { image, ports, resources.requests: { cpu, memoryInGB } }` |
| `restart_policy`, `availability_zone` | `properties.restartPolicy`, `zones` |
| `ip_address_type`, `subnet_id` | `properties.ipAddress: { type, ports }`, `properties.subnetIds` |
| `managed_identity` | `identity: { type, userAssignedIdentities }` |
| `registry_login_server` | `properties.imageRegistryCredentials[]: { server, identity }` |
| `key_management` | `properties.encryptionProperties: { vaultBaseUrl, keyName, keyVersion, identity }` |
| `diagnostic_workspace`, `log_type` | `properties.diagnostics.logAnalytics: { workspaceId, workspaceKey, logType }` |
