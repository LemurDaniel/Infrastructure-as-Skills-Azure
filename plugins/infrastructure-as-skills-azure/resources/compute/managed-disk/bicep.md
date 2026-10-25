# Rendering a Managed Disk as Bicep

Mapping from the question set to the disk. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/managed-disk.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/compute/disk:<version>` | **0.6.1** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `create_option`, `source_resource_id` | `createOption: 'Empty'` / `'Copy'`, `sourceResourceId` | Default `'Empty'`; written |
| `sku` | `sku` | Required; written |
| `size_gb` | `diskSizeGB` | Default `0`; written |
| `zone` | `availabilityZone` | **Required**: `1`, `2`, `3`, or `-1` for none (ZRS type, region without zones) |
| `network_access` | `networkAccessPolicy`, `publicNetworkAccess` | `'DenyAll'` / `'Disabled'` is the module default (Terraform `AllowPrivate`); written. `'AllowPrivate'` needs an id the module has no parameter for |
| `key_management`, `disk_encryption_set_id` | `diskEncryptionSetResourceId` | |
| `role_assignments` | `roleAssignments` | |
| not offered | `maxShares: 1`, `burstingEnabled: false`, `hyperVGeneration` | Written at the defaults so a module release cannot change them |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

The module has no parameter for a disk access resource or a private endpoint, and none for a
diagnostic setting (a disk has none). `allow_private` is therefore the authored resource in
Bicep, with a stated gap, not a module call.

### The call

```bicep
module disk 'br/public:avm/res/compute/disk:0.6.1' = {
  name: 'managed-disk'
  params: {
    name: diskName
    location: location
    tags: tags
    // decision: managed-disk.disk.zone - -1 for a ZRS type or a region without zones
    availabilityZone: 1

    createOption: 'Empty'
    // decision: managed-disk.disk.sku
    sku: 'Premium_LRS'
    diskSizeGB: 128
    maxShares: 1
    burstingEnabled: false

    // decision: managed-disk.networking.network_access - Terraform's module default is AllowPrivate
    networkAccessPolicy: 'DenyAll'
    publicNetworkAccess: 'Disabled'

    diskEncryptionSetResourceId: diskEncryptionSetId // customer_managed only

    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = disk.outputs.resourceId
```

Built with `bicep build` against 0.6.1. Output names are read from the README of the pinned
version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback, and the only form of `allow_private`. `Microsoft.Compute/disks` with `sku` and
`properties`:

| Decision | Property |
|---|---|
| `create_option`, `source_resource_id` | `properties.creationData { createOption, sourceResourceId }` |
| `sku` | `sku.name` |
| `size_gb` | `properties.diskSizeGB` |
| `zone` | `zones: [ '1' ]` |
| `network_access` | `properties.networkAccessPolicy`, `properties.publicNetworkAccess`, `properties.diskAccessId` |
| `key_management` | `properties.encryption { type: 'EncryptionAtRestWithCustomerKey', diskEncryptionSetId }` |
| private endpoint | `Microsoft.Network/privateEndpoints` with group id `disks` |
