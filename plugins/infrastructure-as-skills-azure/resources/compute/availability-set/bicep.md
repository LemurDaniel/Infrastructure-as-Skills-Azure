# Rendering an Availability Set as Bicep

Mapping from the question set to the set and its optional proximity placement group. General
layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/availability-set.bicep
```

## With the AVM module

| Resource | Module | Documented against | Resolved |
|---|---|---|---|
| Availability set | `br/public:avm/res/compute/availability-set:<version>` | **0.2.4** | 2026-10-25 |
| Proximity placement group | `br/public:avm/res/compute/proximity-placement-group:<version>` | **0.4.1** | 2026-10-25 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact versions.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `skuName: 'Aligned'` / `'Classic'` | Default `'Aligned'`; written |
| `fault_domain_count` | `platformFaultDomainCount` | Default `2`; written |
| `update_domain_count` | `platformUpdateDomainCount` | Default `5`; written |
| `proximity_placement_group` | `proximityPlacementGroupResourceId` on the set | The group is a second module call; `null` for none |
| `proximity_zone` | `availabilityZone` on the group | **Required**: `-1` for none |
| `proximity_vm_sizes` | `intent: { vmSizes: [...] }` | |
| not offered | `type: 'Standard'` on the group | `'Ultra'` is for ultra disks - written at the default |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
// decision: availability-set.proximity.proximity_placement_group - rendered only when true
module proximityPlacementGroup 'br/public:avm/res/compute/proximity-placement-group:0.4.1' = {
  name: 'proximity-placement-group'
  params: {
    name: proximityPlacementGroupName
    location: location
    tags: tags
    // decision: availability-set.proximity.proximity_zone - -1 is none; a set's machines have no zone
    availabilityZone: -1
    type: 'Standard'
    intent: { vmSizes: [ 'Standard_D2ds_v5' ] }
    enableTelemetry: true
  }
}

module availabilitySet 'br/public:avm/res/compute/availability-set:0.2.4' = {
  name: 'availability-set'
  params: {
    name: availabilitySetName
    location: location
    tags: tags
    // decision: availability-set.set.sku
    skuName: 'Aligned'
    platformFaultDomainCount: 2
    platformUpdateDomainCount: 5
    proximityPlacementGroupResourceId: proximityPlacementGroup.outputs.resourceId
    enableTelemetry: true
  }
}

output id string = availabilitySet.outputs.resourceId
```

Built with `bicep build` against 0.2.4 and 0.4.1; output names are read from the README of the
pinned versions.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Compute/availabilitySets` with `sku` and `properties`:

| Decision | Property |
|---|---|
| `sku` | `sku.name` |
| `fault_domain_count`, `update_domain_count` | `properties.platformFaultDomainCount`, `properties.platformUpdateDomainCount` |
| `proximity_placement_group` | `properties.proximityPlacementGroup.id` |
| group | `Microsoft.Compute/proximityPlacementGroups` with `properties.proximityPlacementGroupType`, `properties.intent.vmSizes`, `zones` |
