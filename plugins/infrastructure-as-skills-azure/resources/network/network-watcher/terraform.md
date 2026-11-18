# Rendering Network Watcher flow logs as Terraform

Mapping from the question set to the watcher and its flow logs. General layout, variables and
tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-networkwatcher/azurerm` | **v0.3.2** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.2`.

**`azurerm` 4.x with AzAPI children**: it requires `azurerm ~> 4.0` - a root calling it cannot be on
5.x - plus `azapi ~> 2.0` (the flow logs are `azapi_resource`s of type
`Microsoft.Network/networkWatchers/flowLogs@2023-11-01`), `modtm ~> 0.3.0`, `random >= 3.6.2, < 4.0`,
Terraform `>= 1.9`. **It never creates the watcher**: `network_watcher_id`, `network_watcher_name`
and `resource_group_name` (the watcher's group) are required inputs and the module reads the
watcher with a data source. The root's provider set is the union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Decision | Input | Note |
|---|---|---|
| (format) | `flow_logs.<k>.version = 2` | No question: version 2 is the only one that carries flow state and bytes; written |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.3.2: the watcher itself (above) and the flow log's
`enabledFilteringCriteria`, which the question set has no decision for. `lock` is an input the
question set has no decision for - leave it `null`.

### The call

```hcl
data "naming_name" "flow_log" {
  resource   = "Azure::Microsoft.Network/networkWatchers"
  parameters = { name = "${var.workload}-vnet-flowlog" }
}

# decision: network-watcher.watcher.ownership - platform: the auto-created watcher is read, never created
data "azurerm_network_watcher" "this" {
  name                = "NetworkWatcher_${var.location}"
  resource_group_name = "NetworkWatcherRG"
}

data "azurerm_log_analytics_workspace" "this" {
  name                = var.diagnostic_workspace.name
  resource_group_name = var.diagnostic_workspace.resource_group_name
}

module "network_watcher" {
  source  = "Azure/avm-res-network-networkwatcher/azurerm"
  version = "~> 0.3.2"

  location             = var.location
  network_watcher_id   = data.azurerm_network_watcher.this.id
  network_watcher_name = data.azurerm_network_watcher.this.name
  resource_group_name  = data.azurerm_network_watcher.this.resource_group_name

  # decision: network-watcher.flow_logs.flow_log_targets - one entry per network
  flow_logs = {
    vnet = {
      enabled            = true
      name               = data.naming_name.flow_log.name
      target_resource_id = module.virtual_network.resource_id
      # decision: network-watcher.flow_logs.flow_log_storage_account
      storage_account_id = module.storage_logs.resource_id
      # decision: network-watcher.flow_logs.retention_days
      retention_policy = { days = 30, enabled = true }
      version          = 2
      # decision: network-watcher.flow_logs.traffic_analytics, traffic_analytics_interval_minutes, traffic_analytics_workspace
      traffic_analytics = {
        enabled               = true
        interval_in_minutes   = 60
        workspace_id          = data.azurerm_log_analytics_workspace.this.workspace_id
        workspace_region      = data.azurerm_log_analytics_workspace.this.location
        workspace_resource_id = data.azurerm_log_analytics_workspace.this.id
      }
    }
  }
  # decision: network-watcher.monitors.connection_monitors
  condition_monitor = null
  # decision: network-watcher.access.role_assignments
  role_assignments = {}

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "flow_log_ids" { value = { for k, f in module.network_watcher.resource_flow_log : k => f.id } }
```

Validated with `terraform validate` (registry, v0.3.2, `azurerm ~> 4.0`, `azapi ~> 2.0`). For
`ownership: deployment` the data source becomes

```hcl
resource "azurerm_network_watcher" "this" {
  name                = data.naming_name.network_watcher.name
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tags
}
```

and its `id`, `name` and `resource_group_name` feed the module.

### Tests

`mock_provider "azurerm"` with a `mock_data "azurerm_network_watcher"` whose `id` parses (the module's
own data source reads it too), `"azapi"`, `"modtm"` and `"random"`; the naming provider stays real.
The module's `resource_flow_log` output is the map of `azapi_resource`s, whose `body` is what the
root passed in and is **known at plan**, so the flow-log decisions are asserted there; the watcher
reference and the monitors are not. Settled by a `terraform test` run on v0.3.2:

```hcl
run "flow_logs" {
  command = plan

  # decision: network-watcher.flow_logs.retention_days
  assert {
    condition     = module.network_watcher.resource_flow_log["vnet"].body.properties.retentionPolicy.days == 30
    error_message = "Flow logs are kept 30 days."
  }
  # decision: network-watcher.flow_logs.traffic_analytics_interval_minutes
  assert {
    condition     = module.network_watcher.resource_flow_log["vnet"].body.properties.flowAnalyticsConfiguration.networkWatcherFlowAnalyticsConfiguration.trafficAnalyticsInterval == 60
    error_message = "Traffic analytics runs every 60 minutes."
  }
  # decision: network-watcher.flow_logs.flow_log_targets
  assert {
    condition     = module.network_watcher.resource_flow_log["vnet"].body.properties.targetResourceId == var.virtual_network_id
    error_message = "The flow log targets the virtual network."
  }
}

# `.body.properties.storageId` (flow_log_storage_account), `.flowAnalyticsConfiguration.networkWatcherFlowAnalyticsConfiguration.enabled`
# (traffic_analytics) and `.workspaceResourceId` (traffic_analytics_workspace) are asserted the same way.
# not-testable: network-watcher.watcher.ownership - a data source under platform; the plan shows the mocked id only
# not-testable: network-watcher.monitors.connection_monitors - azurerm_network_connection_monitor inside the module, no output of its body
# not-testable: network-watcher.access.role_assignments - inside the module
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Resource / argument |
|---|---|
| the flow log | `azurerm_network_watcher_flow_log` (`network_watcher_name`, `resource_group_name` = the watcher's group, `name`, `location`, `target_resource_id`, `storage_account_id`, `enabled`, `version = 2`) |

Validated against `azurerm` 5.x; the arguments match the module's shape one to one.
