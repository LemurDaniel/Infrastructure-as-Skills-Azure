# Rendering a data collection rule as Bicep

Mapping from the question set to the rule, its endpoint and the associations. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/data-collection.bicep
```

## With the AVM modules

| Resource | Module | Documented against | Resolved |
|---|---|---|---|
| Data collection rule | `br/public:avm/res/insights/data-collection-rule:<version>` | **0.11.0** | 2026-10-26 |
| Data collection endpoint (`endpoint: create`) | `br/public:avm/res/insights/data-collection-endpoint:<version>` | **0.5.1** | 2026-10-26 |

Both `Available`. Resolve the current versions and re-read the README parameters before
rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.
The rule module takes one discriminated object, `dataCollectionRuleProperties`, whose `kind`
selects the required members (`Linux`, `Windows`, `All`, `AgentSettings`, `Direct`,
`WorkspaceTransforms`, `PlatformTelemetry`); **`AgentDirectToStore` is not a variant of 0.11.0**
and renders authored.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Parameter | Note |
|---|---|---|
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
// decision: data-collection-rule.data_sources.performance_counter_set - the basic set, Linux spelling
var linuxBasicCounters = [
  'Processor(*)\\% Processor Time'
  'Processor(*)\\% Idle Time'
  'Memory(*)\\% Used Memory'
  'Memory(*)\\Available MBytes Memory'
  'Memory(*)\\% Used Swap Space'
  'Logical Disk(*)\\% Used Space'
  'Logical Disk(*)\\Free Megabytes'
  'Logical Disk(*)\\Disk Transfers/sec'
  'Network(*)\\Total Bytes Received'
  'Network(*)\\Total Bytes Transmitted'
]

// decision: data-collection-rule.endpoint.endpoint - create
module dataCollectionEndpoint 'br/public:avm/res/insights/data-collection-endpoint:0.5.1' = {
  name: 'data-collection-endpoint'
  params: {
    name: dataCollectionEndpointName
    location: location
    tags: tags
    // the rule's kind
    kind: 'Linux'
    // decision: data-collection-rule.networking.endpoint_public_access - module default Disabled, Terraform Enabled
    publicNetworkAccess: 'Enabled'
    enableTelemetry: true
  }
}

module dataCollectionRule 'br/public:avm/res/insights/data-collection-rule:0.11.0' = {
  name: 'data-collection-rule'
  params: {
    name: dataCollectionRuleName
    location: location
    tags: tags
    dataCollectionRuleProperties: {
      // decision: data-collection-rule.rule.kind
      kind: 'Linux'
      // decision: data-collection-rule.endpoint.endpoint
      dataCollectionEndpointResourceId: dataCollectionEndpoint.outputs.resourceId
      dataSources: {
        performanceCounters: [
          {
            name: 'perf-basic'
            // decision: data-collection-rule.data_sources.performance_counter_set, custom_performance_counters
            counterSpecifiers: linuxBasicCounters
            // decision: data-collection-rule.data_sources.performance_sampling_seconds
            samplingFrequencyInSeconds: 60
            // decision: data-collection-rule.destinations.azure_monitor_metrics - both streams
            streams: ['Microsoft-Perf', 'Microsoft-InsightsMetrics']
          }
        ]
        syslog: [
          {
            // decision: data-collection-rule.data_sources.syslog_facilities, syslog_min_level - Warning and above
            name: 'syslog-warning'
            facilityNames: ['cron', 'daemon', 'kern', 'syslog', 'user']
            logLevels: ['Warning', 'Error', 'Critical', 'Alert', 'Emergency']
            streams: ['Microsoft-Syslog']
          }
          {
            // auth and authpriv at Info: a successful login is the evidence
            name: 'syslog-auth'
            facilityNames: ['auth', 'authpriv']
            logLevels: ['Info', 'Notice', 'Warning', 'Error', 'Critical', 'Alert', 'Emergency']
            streams: ['Microsoft-Syslog']
          }
        ]
        // decision: data-collection-rule.data_sources.custom_text_logs, extensions - none
      }
      destinations: {
        // decision: data-collection-rule.destinations.workspace
        logAnalytics: [ { name: 'workspace', workspaceResourceId: workspaceId } ]
        // decision: data-collection-rule.destinations.azure_monitor_metrics
        azureMonitorMetrics: { name: 'metrics' }
      }
      dataFlows: [
        { streams: ['Microsoft-Perf'], destinations: ['workspace'] }
        { streams: ['Microsoft-InsightsMetrics'], destinations: ['metrics'] }
        // decision: data-collection-rule.data_sources.transformations - content, loaded from the file
        { streams: ['Microsoft-Syslog'], destinations: ['workspace'], transformKql: loadTextContent('dcr/syslog.kql') }
      ]
      // decision: data-collection-rule.data_sources.stream_declarations - none
      streamDeclarations: {}
    }
    // decision: data-collection-rule.identity.managed_identity - none
    enableTelemetry: true
  }
}

// decision: data-collection-rule.associations.associations - wiring, one per machine
resource vm 'Microsoft.Compute/virtualMachines@2024-07-01' existing = [for id in associations: {
  name: last(split(id, '/'))
}]

resource ruleAssociation 'Microsoft.Insights/dataCollectionRuleAssociations@2023-03-11' = [for (id, i) in associations: {
  name: 'dcra-${dataCollectionRuleName}'
  scope: vm[i]
  properties: {
    dataCollectionRuleId: dataCollectionRule.outputs.resourceId
  }
}]

// the endpoint association carries the fixed name and no rule
resource endpointAssociation 'Microsoft.Insights/dataCollectionRuleAssociations@2023-03-11' = [for (id, i) in associations: {
  name: 'configurationAccessEndpoint'
  scope: vm[i]
  properties: {
    dataCollectionEndpointId: dataCollectionEndpoint.outputs.resourceId
  }
}]

output dataCollectionRuleId string = dataCollectionRule.outputs.resourceId
```

The `existing` machines must be in the same resource group as the module, or carry a `scope:`;
a machine in another group gets its association from the module that renders the machine. The
rule's own diagnostic setting (`diagnostic_workspace`, `diagnostic_categories`) is an authored
`Microsoft.Insights/diagnosticSettings@2021-05-01-preview` with `scope:` an `existing` reference
to the rule by `dataCollectionRule.outputs.name`, `logs: [ { category: 'LogErrors', enabled: true } ]`.
Built with `bicep build` against 0.11.0 / 0.5.1 on 2026-10-26.

### Tests

`dataCollectionRuleProperties` is one parameter of the nested deployment, so every decision
inside it is a path under `properties.parameters.dataCollectionRuleProperties.value.*`
(`kind`, `dataSources.syslog[0].logLevels`, `destinations.logAnalytics[0].workspaceResourceId`
matched on the parameter reference, `dataFlows[2].transformKql` matched on a line of the KQL);
the endpoint's `publicNetworkAccess` and `kind` are its own parameters. The associations compile
to a `copy` and are matched on `configurationAccessEndpoint` in the expression text
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback, and the path for `AgentDirectToStore`. `Microsoft.Insights/dataCollectionRules@2023-03-11`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
