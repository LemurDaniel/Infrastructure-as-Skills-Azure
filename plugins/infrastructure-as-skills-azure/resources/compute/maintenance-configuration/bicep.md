# Rendering a maintenance configuration as Bicep

Mapping from the question set to `Microsoft.Maintenance/maintenanceConfigurations`. General
layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/maintenance-configuration.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/maintenance/maintenance-configuration:<version>` | **0.4.0** | 2026-11-01 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

The module passes `maintenanceWindow`, `installPatches` and `extensionProperties` through as the
ARM shape (`resourceInput<...@2023-04-01>`), so the property names are ARM's. It writes
`installPatches` only while the scope is `InGuestPatch`.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| (the configuration) | `name` | Assembled from the `mc` abbreviation, affix, workload and the role `patch` |
| (scope `InGuestPatch`) | `extensionProperties: { InGuestPatchMode: 'User' }` | Written with the scope, never asked |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: the assignment - it is the machine's
(`maintenanceConfigurationResourceId` on the virtual-machine module). `namespace`, `lock` and
`roleAssignments` are parameters the question set has no decision for - leave them unset.
**The module defaults `maintenanceScope` to `Host`**: always write the scope.

### The call

```bicep
module maintenanceConfiguration 'br/public:avm/res/maintenance/maintenance-configuration:0.4.0' = {
  name: 'maintenance-configuration'
  params: {
    name: maintenanceConfigurationName
    location: location
    tags: tags

    // decision: maintenance-configuration.schedule.scope - the module default is Host
    maintenanceScope: 'InGuestPatch'
    extensionProperties: {
      InGuestPatchMode: 'User'
    }
    // decision: maintenance-configuration.patches.visibility
    visibility: 'Custom'

    maintenanceWindow: {
      startDateTime: '${maintenanceStartDate} ${maintenanceStartTime}' // decision: schedule.start_date + schedule.start_time - per stage
      duration: '03:00'                                                // decision: maintenance-configuration.schedule.duration
      timeZone: 'UTC'                                                  // decision: maintenance-configuration.schedule.time_zone
      recurEvery: maintenanceRecurEvery                                // decision: maintenance-configuration.schedule.recur_every - per stage
    }

    installPatches: {
      rebootSetting: 'IfRequired' // decision: maintenance-configuration.patches.reboot_setting
      // decision: maintenance-configuration.patches.operating_systems - one object per listed system
      linuxParameters: {
        classificationsToInclude: [ 'Critical', 'Security' ]
        packageNameMasksToExclude: []
        packageNameMasksToInclude: []
      }
      windowsParameters: {
        classificationsToInclude: [ 'Critical', 'Security' ]
        kbNumbersToExclude: []
        kbNumbersToInclude: []
        excludeKbsRequiringReboot: false
      }
    }

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = maintenanceConfiguration.outputs.resourceId
```

Validated with `bicep build` against the published module. The output `resourceId` is what the
virtual-machine module takes as `maintenanceConfigurationResourceId`, beside `patchMode:
'AutomaticByPlatform'` and `bypassPlatformSafetyChecksOnUserSchedule: true`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)):
`maintenanceScope` is `InGuestPatch` with `extensionProperties.InGuestPatchMode` `User`, the
window's four fields, `rebootSetting`, and one parameter object per listed operating system with
its classifications and exclusions. The scope is the one to assert on purpose - the module's
default is the other value.

## Authored rendering

The fallback. `Microsoft.Maintenance/maintenanceConfigurations@2023-04-01` with
`properties.maintenanceScope`, `properties.visibility`, `properties.extensionProperties`,
`properties.maintenanceWindow { startDateTime, duration, timeZone, recurEvery }` and
`properties.installPatches { rebootSetting, linuxParameters, windowsParameters }`. The
assignment is `Microsoft.Maintenance/configurationAssignments@2023-04-01` as an extension
resource with `scope:` the machine, `properties { maintenanceConfigurationId, resourceId }`.
Validated with `bicep build`.
