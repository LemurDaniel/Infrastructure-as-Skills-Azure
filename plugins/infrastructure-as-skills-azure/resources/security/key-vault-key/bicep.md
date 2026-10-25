# Rendering a Key Vault key as Bicep

Mapping from the question set to the key. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/key.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/key-vault/vault/key:<version>` | **0.1.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module is
`Available`, a child module of the Key Vault module; the vault module's own `keys` parameter takes the
same members and is what the `key-vault` set uses for its customer-managed keys.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `key_vault` | `keyVaultName` | The vault, by name, in the same resource group |
| name | `name` | |
| `algorithm`, `protection` | `kty` | `RSA`, `RSA-HSM`, `EC`, `EC-HSM`. **Module default is `EC`**; written. An HSM type needs a Premium vault |
| `key_size` | `keySize` | RSA only |
| `curve` | `curveName` | EC only. Module default `P-256` |
| `key_operations` | `keyOps` | Unset by default (the type's operations); written. Allowed: `decrypt`, `encrypt`, `import`, `sign`, `unwrapKey`, `verify`, `wrapKey` |
| `rotation_days` | `rotationPolicy.lifetimeActions[ { action: { type: 'rotate' }, trigger: { timeAfterCreate } } ]` | ISO 8601 (`P90D`) |
| `expiry_days` | `rotationPolicy.attributes.expiryTime` | Dates each version a rotation creates |
| `notify_days_before_expiry` | `rotationPolicy.lifetimeActions[ { action: { type: 'notify' }, trigger: { timeBeforeExpiry } } ]` | Duration **before** expiry (`P30D`), not an offset from creation |
| `role_assignments` | `roleAssignments: [ { roleDefinitionIdOrName, principalId, principalType } ]` | Scoped to the key. The module knows a fixed set of role names (including `Key Vault Crypto User`, `Key Vault Crypto Service Encryption User`); read the list from the README |
| `context.tags` | `tags` | |
| `deployment.module_telemetry` | `enableTelemetry` | |

### The call

```bicep
module key 'br/public:avm/res/key-vault/vault/key:0.1.1' = {
  name: 'key-storage-cmk'
  params: {
    keyVaultName: keyVaultName
    name: 'key-storage-cmk'

    // decision: key-vault-key.security.algorithm / protection - the module default is EC
    kty: 'RSA'
    // decision: key-vault-key.security.key_size
    keySize: 3072
    // decision: key-vault-key.security.key_operations
    keyOps: [ 'wrapKey', 'unwrapKey' ]

    // decision: key-vault-key.data_protection.rotation_days / expiry_days / notify_days_before_expiry
    rotationPolicy: {
      attributes: { expiryTime: 'P365D' }
      lifetimeActions: [
        {
          action: { type: 'rotate' }
          trigger: { timeAfterCreate: 'P90D' }
        }
        {
          action: { type: 'notify' }
          trigger: { timeBeforeExpiry: 'P30D' }
        }
      ]
    }

    // decision: key-vault-key.identity.role_assignments
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Crypto Service Encryption User'
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
      }
    ]
    tags: tags
    enableTelemetry: true
  }
}

output keyUri string = key.outputs.keyUri
output keyResourceId string = key.outputs.resourceId
```

The call was built with `bicep build` against the version in the table. Outputs are `keyUri`,
`keyUriWithVersion`, `name`, `resourceId` and `resourceGroupName`; the consumer takes `keyUri`
(without the version) so it follows rotations. Names are read from the README of the pinned version.

The module sets no `attributesExp` here: `expiry_days` dates the versions rotation creates. The
module takes an epoch for the first version (`attributesExp`), which would have to be computed from
`utcNow()` and moves on every deployment; a first version that must itself expire is rendered
authored.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. A `Microsoft.KeyVault/vaults/keys` child of the vault:

| Decision | Property |
|---|---|
| `algorithm`, `protection` | `properties.kty` |
| `key_size` | `properties.keySize` |
| `curve` | `properties.curveName` |
| `key_operations` | `properties.keyOps` |
| `rotation_days`, `expiry_days`, `notify_days_before_expiry` | `properties.rotationPolicy: { attributes: { expiryTime }, lifetimeActions: [ ... ] }` |
| first version expiry | `properties.attributes.exp` (epoch seconds) |
| `role_assignments` | `Microsoft.Authorization/roleAssignments` with `scope` set to the key |

```bicep
resource key 'Microsoft.KeyVault/vaults/keys@2024-11-01' = {
  parent: vault
  name: 'key-storage-cmk'
  properties: {
    kty: 'RSA'
    keySize: 3072
    keyOps: [ 'wrapKey', 'unwrapKey' ]
    rotationPolicy: {
      attributes: { expiryTime: 'P365D' }
      lifetimeActions: [
        { action: { type: 'rotate' }, trigger: { timeAfterCreate: 'P90D' } }
        { action: { type: 'notify' }, trigger: { timeBeforeExpiry: 'P30D' } }
      ]
    }
  }
}
```
