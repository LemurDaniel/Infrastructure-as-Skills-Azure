# Rendering a user-assigned identity as Bicep

Mapping from the question set to the identity. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/identity.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/managed-identity/user-assigned-identity:<version>` | **0.6.0** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'identity'
  params: {
    name: identityName
    location: location
    tags: union(tags, { purpose: purpose })

    // decision: user-assigned-identity.identity.federated_credentials
    federatedIdentityCredentials: [
      {
        name: 'github-production'
        issuer: 'https://token.actions.githubusercontent.com'
        subject: 'repo:org/repo:environment:production'
        audiences: [ 'api://AzureADTokenExchange' ]
      }
    ]
    // decision: user-assigned-identity.identity.isolation_scope
    isolationScope: 'None'

    enableTelemetry: true
  }
}

output id string = identity.outputs.resourceId
output principalId string = identity.outputs.principalId
output clientId string = identity.outputs.clientId
```

Output names are read from the README of the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Resource |
|---|---|
| the identity | `Microsoft.ManagedIdentity/userAssignedIdentities`, `properties.isolationScope` |
