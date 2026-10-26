# Rendering Network Watcher flow logs as Bicep

Mapping from the question set to `Microsoft.Network/networkWatchers` and its `flowLogs` children.
General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/network-watcher.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/network-watcher/flow-log:<version>` (child, `ownership: platform`) | **0.1.0** | 2026-10-26 |
| `br/public:avm/res/network/network-watcher:<version>` (parent, `ownership: deployment`) | **0.5.1** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. Two modules
because the parent **always declares the watcher resource**: deployed into `NetworkWatcherRG`
under the auto-created name it is an idempotent PUT on the existing watcher, which works but makes
the render own a resource it did not create. The child module references the watcher by name and
owns only the flow log; it is the `platform` render. Both carry the same flow-log parameters.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `ownership: platform` | the `flow-log` child module, `scope: resourceGroup('NetworkWatcherRG')`, `networkWatcherName: 'NetworkWatcher_${location}'` | The module's own default for the name is the same expression; written |
| `ownership: deployment` | the parent module with `name`, `location` and `flowLogs: [ ... ]` | |
| `location` | `location` | |
| `resource_group_name` | the parent module's deployment scope (`deployment`); `NetworkWatcherRG` for the flow logs (`platform`) | |
| `flow_log_targets` | `targetResourceId` (child) / `flowLogs[].targetResourceId` (parent) | One child module call, or one array entry, per target. The parameter's description still says "NSG"; a virtual network, subnet or interface id is accepted by the resource type |
| `flow_log_storage_account` | `storageResourceId` / `flowLogs[].storageResourceId` | |
| `retention_days` | `retentionInDays` / `flowLogs[].retentionInDays` | Module default **365**; written. 0 renders `retentionPolicy.enabled: false` |
| `traffic_analytics` | the presence of `workspaceResourceId` | The module switches analytics on when a workspace is given; `false` is the absence of the parameter, and the handover says so |
| `traffic_analytics_interval_minutes` | `trafficAnalyticsInterval` / `flowLogs[].trafficAnalyticsInterval` | `10` or `60`; module default 60; written |
| `traffic_analytics_workspace` | `workspaceResourceId` / `flowLogs[].workspaceResourceId` | The id alone; the module derives nothing else |
| (format) | `formatVersion: 2` | Module default 2; written |
| `connection_monitors` | parent `connectionMonitors: [ { name, endpoints, testConfigurations, testGroups, workspaceResourceId } ]`, or the `network-watcher/connection-monitor` child module under `platform` | |
| `role_assignments` | parent `roleAssignments` | The child module has none: under `platform` a role assignment on Azure's watcher is an extension resource in `NetworkWatcherRG` |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the modules: nothing from this question set. `enabledFilteringCriteria` and the
parent's `lock` are parameters the question set has no decision for - leave them unset.

### The call

```bicep
targetScope = 'subscription' // the flow log lands in NetworkWatcherRG, not in the deployment's group

// decision: network-watcher.watcher.ownership - platform: the flow log is a child of the auto-created watcher
module vnetFlowLog 'br/public:avm/res/network/network-watcher/flow-log:0.1.0' = {
  name: 'vnet-flow-log'
  scope: resourceGroup('NetworkWatcherRG')
  params: {
    networkWatcherName: 'NetworkWatcher_${location}'
    name: flowLogName
    location: location
    tags: tags

    // decision: network-watcher.flow_logs.flow_log_targets
    targetResourceId: virtualNetworkId
    // decision: network-watcher.flow_logs.flow_log_storage_account
    storageResourceId: flowLogStorageAccountId
    enabled: true
    formatVersion: 2
    // decision: network-watcher.flow_logs.retention_days - the module default is 365
    retentionInDays: 30
    // decision: network-watcher.flow_logs.traffic_analytics, traffic_analytics_workspace - the workspace's presence switches analytics on
    workspaceResourceId: diagnosticWorkspaceId
    // decision: network-watcher.flow_logs.traffic_analytics_interval_minutes
    trafficAnalyticsInterval: 60

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output flowLogId string = vnetFlowLog.outputs.resourceId
```

For `ownership: deployment`, at resource-group scope:

```bicep
module networkWatcher 'br/public:avm/res/network/network-watcher:0.5.1' = {
  name: 'network-watcher'
  params: {
    name: networkWatcherName
    location: location
    tags: tags
    flowLogs: [
      {
        name: flowLogName
        targetResourceId: virtualNetworkId
        storageResourceId: flowLogStorageAccountId
        enabled: true
        formatVersion: 2
        retentionInDays: 30
        workspaceResourceId: diagnosticWorkspaceId
        trafficAnalyticsInterval: 60
      }
    ]
    connectionMonitors: []
    roleAssignments: []
    enableTelemetry: false
  }
}
```

Both validated with `bicep build` against the published modules. A root that is otherwise at
resource-group scope renders the `platform` form as a subscription-scoped module file of its own,
because a module's `scope` can name another group only from a scope above it.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)):
`networkWatcherName` (the expression's text names `NetworkWatcher_`), `targetResourceId`,
`storageResourceId`, `retentionInDays`, `trafficAnalyticsInterval`, `workspaceResourceId`.
`traffic_analytics: false` is the **absence** of `workspaceResourceId` and is asserted as that;
`ownership` is which module is called and the `resourceGroup` of the nested deployment.

## Authored rendering

The fallback. Under `platform`: `Microsoft.Network/networkWatchers@2024-10-01` as `existing` in
`NetworkWatcherRG` and `Microsoft.Network/networkWatchers/flowLogs@2024-10-01` with `parent`,
`properties.targetResourceId`, `storageId`, `enabled`, `retentionPolicy: { days, enabled }`,
`format: { type: 'JSON', version: 2 }` and
`flowAnalyticsConfiguration.networkWatcherFlowAnalyticsConfiguration: { enabled, workspaceResourceId, trafficAnalyticsInterval }`.
Under `deployment` the watcher is a resource with `location` and empty `properties`. Connection
monitors are `networkWatchers/connectionMonitors` children. Validated with `bicep build`.
