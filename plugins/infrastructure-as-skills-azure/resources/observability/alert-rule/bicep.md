# Rendering an alert rule as Bicep

Mapping from the question set to the three alert resources, chosen by `kind`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/alerts.bicep
```

## With the AVM modules

| Kind | Module | Documented against | Resolved |
|---|---|---|---|
| `metric` | `br/public:avm/res/insights/metric-alert:<version>` | **0.4.1** | 2026-10-26 |
| `log_query` | `br/public:avm/res/insights/scheduled-query-rule:<version>` | **0.6.1** | 2026-10-26 |
| `activity_log` | `br/public:avm/res/insights/activity-log-alert:<version>` | **0.4.2** | 2026-10-26 |

All three `Available`. Resolve the current versions and re-read the README parameters before
rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | `metric` | `log_query` | `activity_log` |
|---|---|---|---|
| `location` | `location: 'global'` (module default `'global'`) | `location` (default `resourceGroup().location`) | `location: 'global'` |
| `action_group` | `actions: [ <id> ]` (strings) | `actions: { actionGroupResourceIds: [ <id> ] }` | `actions: [ { actionGroupId } ]` |
| `severity` | `severity` (module default **3**) | `severity` (module default **3**) | - |
| `enabled` | `enabled` | `enabled` | `enabled` |
| `auto_mitigate` | `autoMitigate` | `autoMitigate` | - |
| `scopes` | `scopes` (module default **the subscription**), `targetResourceType`, `targetResourceRegion` | `scopes: [ workspace id ]` | `scopes: [ subscription().id ]` |
| `metric_name`, `aggregation`, `operator`, `threshold`, `dimensions` | `criteria: { 'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria', allof: [ { criterionType: 'StaticThresholdCriterion', metricNamespace, metricName, timeAggregation, operator, threshold, dimensions } ] }` | | |
| `threshold_mode: dynamic`, `dynamic_sensitivity` | `criterionType: 'DynamicThresholdCriterion'`, `alertSensitivity`, `failingPeriods` | | |
| `window_size`, `frequency` | `windowSize` (module default **PT15M**), `evaluationFrequency` | | |
| `query_file` | | `criterias.allOf[].query: loadTextContent('queries/<rule>.kql')` | |
| `time_aggregation`, `log_operator`, `log_threshold` | | `criterias.allOf[].timeAggregation`, `.operator`, `.threshold` (+ `metricMeasureColumn` for non-Count), `failingPeriods` | |
| `evaluation_frequency`, `window_duration` | | `evaluationFrequency`, `windowSize` (required for `kind: 'LogAlert'`) | |
| `mute_actions_duration` | | `muteActionsDuration` (left out for `none`) | |
| `query_identity`, `user_assigned_identity_id` | | `managedIdentities: { userAssignedResourceIds }` | |
| `category`, `service_health_event_types`, `impacted_regions`, `resource_health_statuses`, `operation_name` | | | `conditions: [ { field, equals } , { anyOf: [...] }, { field, containsAny } ]` |
| `deployment.resource_lock` | `lock` | `lock` | `lock` |
| `deployment.module_telemetry` | `enableTelemetry` | `enableTelemetry` | `enableTelemetry` |
| `context.tags` | `tags` | `tags` | `tags` |

### The calls

```bicep
// ---- kind: activity_log -------------------------------------------------------------
module serviceHealthAlert 'br/public:avm/res/insights/activity-log-alert:0.4.2' = {
  name: 'alert-service-health'
  params: {
    name: serviceHealthAlertName
    // decision: alert-rule.placement.location - a global resource
    location: 'global'
    tags: tags
    // decision: alert-rule.activity_log.category - the scope is the stage's subscription
    scopes: [subscription().id]
    conditions: [
      { field: 'category', equals: 'ServiceHealth' }
      // decision: alert-rule.activity_log.service_health_event_types
      {
        anyOf: [
          { field: 'properties.incidentType', equals: 'Incident' }
          { field: 'properties.incidentType', equals: 'ActionRequired' }
          { field: 'properties.incidentType', equals: 'Security' }
        ]
      }
      // decision: alert-rule.activity_log.impacted_regions - empty: the deployment's region and Global
      { field: 'properties.impactedServices[*].ImpactedRegions[*].RegionName', containsAny: ['West Europe', 'Global'] }
    ]
    // decision: alert-rule.rule.action_group
    actions: [ { actionGroupId: actionGroupId } ]
    // decision: alert-rule.rule.enabled
    enabled: alertEnabled
    enableTelemetry: true
  }
}

// ---- kind: metric ---------------------------------------------------------------------
module http5xxAlert 'br/public:avm/res/insights/metric-alert:0.4.1' = {
  name: 'alert-http5xx'
  params: {
    name: http5xxAlertName
    // decision: alert-rule.placement.location - a global resource
    location: 'global'
    tags: tags
    // decision: alert-rule.metric.scopes - type and region read off the ids; the module default scope is the subscription
    scopes: scopes
    targetResourceType: 'Microsoft.Web/sites'
    targetResourceRegion: location
    // decision: alert-rule.rule.severity - module default 3
    severity: 2
    // decision: alert-rule.rule.enabled
    enabled: alertEnabled
    // decision: alert-rule.rule.auto_mitigate
    autoMitigate: true
    // decision: alert-rule.metric.window_size - module default PT15M
    windowSize: 'PT5M'
    // decision: alert-rule.metric.frequency
    evaluationFrequency: 'PT1M'
    // decision: alert-rule.metric.threshold_mode - static
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allof: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'http5xx'
          // decision: alert-rule.metric.metric_name - the namespace is the scope's type
          metricNamespace: 'Microsoft.Web/sites'
          metricName: 'Http5xx'
          // decision: alert-rule.metric.aggregation
          timeAggregation: 'Total'
          // decision: alert-rule.metric.operator
          operator: 'GreaterThan'
          // decision: alert-rule.metric.threshold
          threshold: 10
          // decision: alert-rule.metric.dimensions - none
          dimensions: []
        }
      ]
    }
    // decision: alert-rule.rule.action_group
    actions: [ actionGroupId ]
    enableTelemetry: true
  }
}

// ---- kind: log_query ------------------------------------------------------------------
module errorsAlert 'br/public:avm/res/insights/scheduled-query-rule:0.6.1' = {
  name: 'alert-errors'
  params: {
    name: errorsAlertName
    // decision: alert-rule.placement.location - the workspace's region
    location: location
    tags: tags
    kind: 'LogAlert'
    // decision: alert-rule.log_query.workspace - the rule's scope
    scopes: [workspaceId]
    // decision: alert-rule.rule.severity - module default 3
    severity: 2
    // decision: alert-rule.rule.enabled
    enabled: alertEnabled
    // decision: alert-rule.log_query.evaluation_frequency
    evaluationFrequency: 'PT5M'
    // decision: alert-rule.log_query.window_duration
    windowSize: 'PT5M'
    // decision: alert-rule.rule.auto_mitigate - refused together with muteActionsDuration
    autoMitigate: true
    // decision: alert-rule.log_query.mute_actions_duration - none: the parameter is left out
    criterias: {
      allOf: [
        {
          // decision: alert-rule.log_query.query_file - content, loaded from the file
          query: loadTextContent('queries/errors.kql')
          // decision: alert-rule.log_query.time_aggregation - Count needs no measure column
          timeAggregation: 'Count'
          // decision: alert-rule.log_query.log_operator
          operator: 'GreaterThan'
          // decision: alert-rule.log_query.log_threshold
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    // decision: alert-rule.identity.query_identity, user_assigned_identity_id
    managedIdentities: {
      userAssignedResourceIds: [queryIdentityId]
    }
    // decision: alert-rule.rule.action_group
    actions: {
      actionGroupResourceIds: [actionGroupId]
    }
    enableTelemetry: true
  }
}
```

The `criteria` and `criterias` objects are untyped in the modules (`object`), so a misspelt key
compiles and fails at deployment; the key names above are the ARM schema's. Built with
`bicep build` against the three versions on 2026-10-26.

### Tests

Every parameter above is a `properties.parameters.<param>.value` of the nested deployment and
observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `severity`,
`enabled`, `autoMitigate`, `windowSize`, `evaluationFrequency`, the `criteria.allof[0].*` and
`criterias.allOf[0].*` paths, `conditions[0].equals`, `scopes` (matched on `subscription()` for
the activity log alert). `loadTextContent` inlines the query, so the query decision is matched on
a line of the KQL.

## Authored rendering

The fallback, one resource type per kind:

| Decision | Property |
|---|---|
| `metric` | `Microsoft.Insights/metricAlerts@2018-03-01`, `location: 'global'`, `properties.{ severity, enabled, autoMitigate, windowSize, evaluationFrequency, scopes, targetResourceType, targetResourceRegion, criteria, actions[].actionGroupId }` |
| `log_query` | `Microsoft.Insights/scheduledQueryRules@2023-12-01`, `kind: 'LogAlert'`, `identity`, `properties.{ severity, enabled, autoMitigate, muteActionsDuration, evaluationFrequency, windowSize, scopes, criteria.allOf[], actions.actionGroups[] }` |
| `activity_log` | `Microsoft.Insights/activityLogAlerts@2020-10-01`, `location: 'global'`, `properties.{ enabled, scopes, condition.allOf[], actions.actionGroups[].actionGroupId }` |
