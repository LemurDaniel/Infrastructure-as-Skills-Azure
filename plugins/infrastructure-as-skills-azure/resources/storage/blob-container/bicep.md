# Rendering blob containers as Bicep

Mapping from the question set to the containers. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

A container is a child of a storage account, and the AVM storage account module takes its
containers inside the `blobServices` parameter. **There is no module call of its own:** the
decisions below land in the account's call, rendered by [../storage-account/bicep.md](../storage-account/bicep.md).
Module: `br/public:avm/res/storage/storage-account:0.33.1` (resolved 2026-10-25), pinned there.

## With the AVM module

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

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
carries the containers, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Storage/storageAccounts/blobServices/containers` (parent
`blobServices/default`) with `properties`:

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
