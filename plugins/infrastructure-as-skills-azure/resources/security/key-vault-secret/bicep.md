# Rendering a Key Vault secret as Bicep

Mapping from the question set to the secret. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/key-vault-secret.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/key-vault/vault/secret:<version>` | **0.1.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module is
`Available`, a child module of the Key Vault module.

**The module is used for `value_source: secure_input` only.** It requires a `value` and a redeploy
writes it as a **new version**, so a placeholder passed through it would replace a filled-in value
on every deployment. A placeholder is rendered authored, with `@onlyIfNotExists()` (below).

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter | Note |
|---|---|---|
| name | `name` | |
| `context.tags` | `tags` | |
| `deployment.module_telemetry` | `enableTelemetry` | |

### The call - a secure input

```bicep
param baseTime string = utcNow()

@secure()
param dbConnection string

var expiry = dateTimeToEpoch(dateTimeAdd(baseTime, 'P365D'))

module secret 'br/public:avm/res/key-vault/vault/secret:0.1.1' = {
  name: 'secret-db-connection'
  params: {
    keyVaultName: keyVaultName
    name: 'db-connection'

    // decision: key-vault-secret.security.value_source - secure_input
    value: dbConnection
    // decision: key-vault-secret.security.content_type
    contentType: 'connection-string'
    // decision: key-vault-secret.security.expiry_days
    attributesExp: expiry

    // decision: key-vault-secret.identity.role_assignments
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
      }
    ]
    tags: tags
    enableTelemetry: true
  }
}

output secretUri string = secret.outputs.secretUri
```

`utcNow()` is allowed only as a parameter default, which is why `baseTime` is one. Outputs are `name`,
`resourceId`, `secretUri`, `secretUriWithVersion` and `resourceGroupName`; the consumer takes
`secretUri` (without the version). Names are read from the README of the pinned version. The call was
built with `bicep build` against the version in the table.

### The call - a placeholder

Outside the module, written once:

```bicep
resource vaultRef 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: keyVaultName
}

// decision: key-vault-secret.security.value_source - placeholder
@onlyIfNotExists()
resource placeholder 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = [for name in secretPlaceholders: {
  parent: vaultRef
  name: name
  properties: {
    value: 'placeholder - replace after deployment'
    // decision: key-vault-secret.security.content_type
    contentType: 'text/plain'
    // decision: key-vault-secret.security.expiry_days - the first version only
    attributes: { exp: expiry }
  }
}]
```

The decorator deploys the secret only when it does not exist, so neither the value nor the date
somebody set is overwritten; the toolchain is assumed to be the latest Bicep, as for the vault's
slots, and a Bicep that rejects the decorator is a toolchain to update. If the vault is created in
the same template, give `vaultRef` `dependsOn: [ vault ]` as the `key-vault` set does. The API
version is looked up against the compiled module rather than recalled. Role assignments on a
placeholder are `Microsoft.Authorization/roleAssignments` with `scope: placeholder[<i>]`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so the secure input's decisions are observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). A placeholder is a
plain resource in the compiled ARM; how the decorator shows there is read from a compile, not
recalled, and the placeholder resources are matched by that. The secure value is never in the test.

## Authored rendering

The fallback. A `Microsoft.KeyVault/vaults/secrets` child of the vault; the placeholder block above
is already the authored form.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
