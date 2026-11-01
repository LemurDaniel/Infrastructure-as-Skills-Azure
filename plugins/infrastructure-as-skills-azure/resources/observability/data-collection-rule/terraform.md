# Rendering a data collection rule as Terraform

Mapping from the question set to the rule, its endpoint and the associations. General layout,
variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

| Resource | Module | Documented against | Resolved | Status |
|---|---|---|---|---|
| Data collection rule | `Azure/avm-res-insights-datacollectionrule/azurerm` | **v0.1.0** | 2026-10-26 | Available |
| Data collection endpoint (`endpoint: create`) | `Azure/avm-res-insights-datacollectionendpoint/azurerm` | **v0.2.0** | 2026-10-26 | Available |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pins `~> 0.1.0` and `~> 0.2.0`.

**Both AzAPI only**: `parent_id` (the resource group's id), `azapi ~> 2.4`, `modtm ~> 0.3`,
`random ~> 3.5`, Terraform `>= 1.9`, no `azurerm`. The root keeps `azurerm` 5.x for the
associations (`azurerm_monitor_data_collection_rule_association`), which neither module renders.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Input | Note |
|---|---|---|
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
locals {
  # decision: data-collection-rule.data_sources.performance_counter_set - the basic set, Linux spelling
  linux_basic_counters = [
    "Processor(*)\\% Processor Time", "Processor(*)\\% Idle Time",
    "Memory(*)\\% Used Memory", "Memory(*)\\Available MBytes Memory", "Memory(*)\\% Used Swap Space",
    "Logical Disk(*)\\% Used Space", "Logical Disk(*)\\Free Megabytes", "Logical Disk(*)\\Disk Transfers/sec",
    "Network(*)\\Total Bytes Received", "Network(*)\\Total Bytes Transmitted",
  ]
}

# decision: data-collection-rule.endpoint.endpoint - create
module "data_collection_endpoint" {
  source  = "Azure/avm-res-insights-datacollectionendpoint/azurerm"
  version = "~> 0.2.0"

  name      = data.naming_name.data_collection_endpoint.name
  parent_id = data.azurerm_resource_group.this.id
  location  = var.location
  # the rule's kind
  kind = "Linux"
  # decision: data-collection-rule.networking.endpoint_public_access - module default Enabled, Bicep Disabled
  public_network_access = "Enabled"

  enable_telemetry = true
  tags             = local.tags
}

module "data_collection_rule" {
  source  = "Azure/avm-res-insights-datacollectionrule/azurerm"
  version = "~> 0.1.0"

  name      = data.naming_name.data_collection_rule.name
  parent_id = data.azurerm_resource_group.this.id
  location  = var.location
  # decision: data-collection-rule.rule.kind
  kind = "Linux"
  # decision: data-collection-rule.endpoint.endpoint
  data_collection_endpoint_id = module.data_collection_endpoint.resource_id

  data_sources = {
    performance_counters = [{
      name = "perf-basic"
      # decision: data-collection-rule.data_sources.performance_counter_set, custom_performance_counters
      counter_specifiers = local.linux_basic_counters
      # decision: data-collection-rule.data_sources.performance_sampling_seconds
      sampling_frequency_in_seconds = 60
      # decision: data-collection-rule.destinations.azure_monitor_metrics - both streams
      streams = ["Microsoft-Perf", "Microsoft-InsightsMetrics"]
    }]
    syslog = [
      {
        # decision: data-collection-rule.data_sources.syslog_facilities, syslog_min_level - Warning and above
        name           = "syslog-warning"
        facility_names = ["cron", "daemon", "kern", "syslog", "user"]
        log_levels     = ["Warning", "Error", "Critical", "Alert", "Emergency"]
        streams        = ["Microsoft-Syslog"]
      },
      {
        # auth and authpriv at Info: a successful login is the evidence
        name           = "syslog-auth"
        facility_names = ["auth", "authpriv"]
        log_levels     = ["Info", "Notice", "Warning", "Error", "Critical", "Alert", "Emergency"]
        streams        = ["Microsoft-Syslog"]
      },
    ]
    # decision: data-collection-rule.data_sources.custom_text_logs - none
    log_files = []
    # decision: data-collection-rule.data_sources.extensions - none
    extensions = []
  }

  destinations = {
    # decision: data-collection-rule.destinations.workspace
    log_analytics = [{ name = "workspace", workspace_resource_id = var.workspace_id }]
    # decision: data-collection-rule.destinations.azure_monitor_metrics
    azure_monitor_metrics = { name = "metrics" }
  }

  data_flows = [
    { streams = ["Microsoft-Perf"], destinations = ["workspace"] },
    { streams = ["Microsoft-InsightsMetrics"], destinations = ["metrics"] },
    # decision: data-collection-rule.data_sources.transformations - content, loaded from the file
    { streams = ["Microsoft-Syslog"], destinations = ["workspace"], transform_kql = file("${path.module}/dcr/syslog.kql") },
  ]

  # decision: data-collection-rule.data_sources.stream_declarations - none
  stream_declarations = {}

  # decision: data-collection-rule.identity.managed_identity - none
  managed_identities = {}

  # decision: data-collection-rule.observability.diagnostic_workspace, diagnostic_categories
  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["LogErrors"]
      log_groups            = []
      metric_categories     = []
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

# decision: data-collection-rule.associations.associations - wiring in the root, one per machine
resource "azurerm_monitor_data_collection_rule_association" "rule" {
  for_each                = toset(var.associations)
  name                    = "dcra-${data.naming_name.data_collection_rule.name}"
  target_resource_id      = each.value
  data_collection_rule_id = module.data_collection_rule.resource_id
}

# the endpoint association carries the fixed name and no rule
resource "azurerm_monitor_data_collection_rule_association" "endpoint" {
  for_each                    = toset(var.associations)
  name                        = "configurationAccessEndpoint"
  target_resource_id          = each.value
  data_collection_endpoint_id = module.data_collection_endpoint.resource_id
}

output "data_collection_rule_id" { value = module.data_collection_rule.resource_id }
```

A `Direct`, `AgentDirectToStore` or `WorkspaceTransforms` rule cannot go through the module (its `kind`
validation allows `Linux` and `Windows`) and is the authored resource below. A Windows rule swaps the counters for the Windows dialect
(`\Processor(_Total)\% Processor Time`, `\Memory\Available Bytes`, ...), replaces `syslog` by
`windows_event_logs = [{ name, streams = ["Microsoft-Event"], x_path_queries = [...] }]` and the
endpoint's `kind` by `"Windows"`. Validated with `terraform validate` against v0.1.0 / v0.2.0 and
azurerm 5.11 on 2026-10-26.

### Tests

`mock_provider "azapi"`, `"modtm"` and `"azurerm"`. Both modules expose `resource` (the
`azapi_resource`), so `kind`, `body.properties.dataSources.*`, `.destinations.*`, `.dataFlows[*]`,
`.streamDeclarations`, `.dataCollectionEndpointId` and, on the endpoint,
`body.properties.networkAcls.publicNetworkAccess` are asserted through
`module.data_collection_rule.resource.body` (lists as `jsonencode`). The diagnostic setting is a
child the module builds and carries `# not-testable:`; the associations are the root's own
resources and `target_resource_id` / `name == "configurationAccessEndpoint"` are asserted directly.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
