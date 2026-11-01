# Rendering an alert rule as Terraform

Mapping from the question set to the three alert resources, chosen by `kind`. General layout,
variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

| Kind | Module | Documented against | Resolved | Status |
|---|---|---|---|---|
| `activity_log` | `Azure/avm-res-insights-activitylogalert/azurerm` | **v0.1.0** | 2026-10-26 | Available |
| `metric` | `avm-res-insights-metricalert` | none published | 2026-10-26 | **Proposed** - authored below is the primary |
| `log_query` | `avm-res-insights-scheduledqueryrule` | none published | 2026-10-26 | **Proposed** - authored below is the primary |

Resolve the current status and version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says; the two `Proposed` modules are
re-checked in the index on every render. The activity log alert pin is `~> 0.1.0`.

**The activity log alert module is AzAPI only**: `parent_id` (the resource group's id),
`azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.5`, Terraform `>= 1.9`, no `azurerm`. It takes
`location` for telemetry and `resource_location` (default `global`) for the alert. The two
authored resources use `azurerm` 5.x in the same root.

### Decision -> module input / resource argument

What each decision renders to - the input or argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | `activity_log` (module) | `metric` (`azurerm_monitor_metric_alert`) | `log_query` (`azurerm_monitor_scheduled_query_rules_alert_v2`) |
|---|---|---|---|
| `deployment.resource_lock` | `lock = { kind }` | `azurerm_management_lock` | `azurerm_management_lock` |
| `deployment.module_telemetry` | `enable_telemetry` | - | - |
| `context.tags` | `tags` | `tags` | `tags` |

### The calls

```hcl
# ---- kind: activity_log (AVM) --------------------------------------------------------
module "service_health_alert" {
  source  = "Azure/avm-res-insights-activitylogalert/azurerm"
  version = "~> 0.1.0"

  name      = data.naming_name.service_health_alert.name
  parent_id = data.azurerm_resource_group.this.id
  # decision: alert-rule.placement.location - telemetry region; the alert itself is global
  location          = var.location
  resource_location = "global"

  # decision: alert-rule.activity_log.category - the scope is the stage's subscription
  scopes = ["/subscriptions/${var.subscription_id}"]
  condition = {
    all_of = [
      { field = "category", equals = "ServiceHealth" },
      # decision: alert-rule.activity_log.service_health_event_types
      { any_of = [
        { field = "properties.incidentType", equals = "Incident" },
        { field = "properties.incidentType", equals = "ActionRequired" },
        { field = "properties.incidentType", equals = "Security" },
      ] },
      # decision: alert-rule.activity_log.impacted_regions - empty: the deployment's region and Global
      { field = "properties.impactedServices[*].ImpactedRegions[*].RegionName", contains_any = ["West Europe", "Global"] },
    ]
  }

  # decision: alert-rule.rule.action_group
  action_groups = { primary = { action_group_id = var.action_group_id } }
  # decision: alert-rule.rule.enabled
  enabled = var.alert_enabled

  enable_telemetry = true
  tags             = local.tags
}

# ---- kind: metric (authored, azurerm 5.x; the AVM module is Proposed) -----------------
resource "azurerm_monitor_metric_alert" "this" {
  name                = data.naming_name.http5xx_alert.name
  resource_group_name = var.resource_group_name
  # decision: alert-rule.metric.scopes - type and region read off the ids
  scopes                   = var.scopes
  target_resource_type     = "Microsoft.Web/sites"
  target_resource_location = var.location

  # decision: alert-rule.rule.severity - 0..4, provider default 3
  severity = 2
  # decision: alert-rule.rule.enabled
  enabled = var.alert_enabled
  # decision: alert-rule.rule.auto_mitigate
  auto_mitigate = true
  # decision: alert-rule.metric.window_size
  window_size = "PT5M"
  # decision: alert-rule.metric.frequency
  frequency = "PT1M"

  # decision: alert-rule.metric.threshold_mode - static
  criteria {
    # decision: alert-rule.metric.metric_name - the namespace is the scope's type
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    # decision: alert-rule.metric.aggregation
    aggregation = "Total"
    # decision: alert-rule.metric.operator
    operator = "GreaterThan"
    # decision: alert-rule.metric.threshold
    threshold = 10
    # decision: alert-rule.metric.dimensions - none
  }

  # decision: alert-rule.rule.action_group
  action {
    action_group_id = var.action_group_id
  }

  tags = local.tags
}

# ---- kind: log_query (authored, azurerm 5.x; the AVM module is Proposed) --------------
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "this" {
  name                = data.naming_name.errors_alert.name
  resource_group_name = var.resource_group_name
  # decision: alert-rule.placement.location - the workspace's region
  location = var.location

  # decision: alert-rule.log_query.workspace - the rule's scope
  scopes = [var.workspace_id]
  # decision: alert-rule.rule.severity
  severity = 2
  # decision: alert-rule.rule.enabled
  enabled = var.alert_enabled
  # decision: alert-rule.log_query.evaluation_frequency
  evaluation_frequency = "PT5M"
  # decision: alert-rule.log_query.window_duration
  window_duration = "PT5M"
  # decision: alert-rule.rule.auto_mitigate - refused together with a mute duration
  auto_mitigation_enabled = true
  # decision: alert-rule.log_query.mute_actions_duration - none
  mute_actions_after_alert_duration = null

  criteria {
    # decision: alert-rule.log_query.query_file - content, loaded from the file
    query = file("${path.module}/queries/errors.kql")
    # decision: alert-rule.log_query.time_aggregation - Count needs no measure column
    time_aggregation_method = "Count"
    # decision: alert-rule.log_query.log_operator
    operator = "GreaterThan"
    # decision: alert-rule.log_query.log_threshold
    threshold = 0
  }

  # decision: alert-rule.identity.query_identity, user_assigned_identity_id
  identity {
    type         = "UserAssigned"
    identity_ids = [var.query_identity_id]
  }

  # decision: alert-rule.rule.action_group
  action {
    action_groups = [var.action_group_id]
  }

  tags = local.tags
}
```

A dynamic metric alert replaces the `criteria` block by `dynamic_criteria { metric_namespace,
metric_name, aggregation, operator, alert_sensitivity }`. The Service Health region name is the
display name (`West Europe`), mapped from `var.location` by a local. Validated with
`terraform validate` against the activity log alert module v0.1.0 and azurerm 5.11 on 2026-10-26.

### Tests

`mock_provider "azurerm"`, `"azapi"` and `"modtm"`. The two authored resources expose every
argument at plan time: `severity`, `enabled`, `auto_mitigate`, `window_size`, `frequency`,
`criteria[0].*`, `action[0].action_group_id` on the metric alert; `evaluation_frequency`,
`window_duration`, `criteria[0].query` (compared with `file()` of the same path),
`identity[0].type`, `scopes` (as `jsonencode`) on the query rule - one assert per decision. The
activity log alert module exposes **`resource_id` only**, so its decisions (`category`,
`service_health_event_types`, `impacted_regions`, `action_group`, `enabled`) carry
`# not-testable: <key> - the module exposes no attribute; the call is the review`.

## Authored rendering

For `metric` and `log_query` the authored resources above **are** the rendering (no module).
The activity log alert's fallback is authored.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
