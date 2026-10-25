# Rendering blob containers as Bicep

Mapping from the question set to the containers. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

A container is a child of a storage account, and the AVM storage account module takes its
containers inside the `blobServices` parameter. **There is no module call of its own:** the
decisions below land in the account's call, rendered by [../storage-account/bicep.md](../storage-account/bicep.md).
Module: `br/public:avm/res/storage/storage-account:0.33.1` (resolved 2026-10-25), pinned there.

## With the AVM module

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `container_names` | `blobServices.containers: [ { name } ]` | |
| `public_access` | `blobServices.containers[].publicAccess` | `'None'`, `'Blob'`, `'Container'`; written. The account must allow anonymous access (`allowBlobPublicAccess`) for anything but `'None'` |
| `immutable_storage` | `blobServices.containers[].immutableStorageWithVersioningEnabled` | Needs `blobServices.isVersioningEnabled`; **cannot be combined with `restorePolicyEnabled`** |
| `encryption_scope_locked` | `blobServices.containers[].denyEncryptionScopeOverride`, `defaultEncryptionScope` | Both or neither: Azure refuses a container with one of them (`ContainerOperationFailure`, missing `x-ms-default-encryption-scope` / `x-ms-deny-encryption-scope-override`). `false` with no scope writes neither |
| `role_assignments` | `blobServices.containers[].roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |

```bicep
    // inside module storage - decision: blob-container.containers.*
    blobServices: {
      containers: [for c in containerNames: {
        name: c
        publicAccess: 'None'
        immutableStorageWithVersioningEnabled: false
      }]
    }
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.blobServices.value`
carries the containers, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Storage/storageAccounts/blobServices/containers` (parent
`blobServices/default`) with `properties`:

| Decision | Property |
|---|---|
| `public_access` | `properties.publicAccess` |
| `immutable_storage` | `properties.immutableStorageWithVersioning: { enabled }` |
| `encryption_scope_locked` | `properties.denyEncryptionScopeOverride`, `defaultEncryptionScope` - written together, or both left out when no scope is set |
