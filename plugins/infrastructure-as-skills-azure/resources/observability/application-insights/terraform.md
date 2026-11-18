# Rendering Application Insights as Terraform

Mapping from the question set to the component. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-insights-component/azurerm` | **v0.5.0** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.5.0`.

**AzAPI only**: it takes `parent_id` (the resource group's id) and requires `azapi ~> 2.12` and
`time ~> 0.13`, Terraform `>= 1.9`; no `azurerm` and no `modtm`. The root's provider set is the
union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Decision | Input | Note |
|---|---|---|
| (retention) | `retention_in_days` | Module default 90; set to the workspace's retention, not a decision |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "insights" {
  source  = "Azure/avm-res-insights-component/azurerm"
  version = "~> 0.5.0"

  name         = data.naming_name.insights.name
  location     = var.location
  parent_id    = data.azurerm_resource_group.this.id
  workspace_id = var.workspace_id

  application_type = "web"
  # decision: application-insights.component.sampling_percentage / daily_cap_gb
  sampling_percentage  = 100
  daily_data_cap_in_gb = 0
  # decision: application-insights.component.store_client_ip - disabling the masking stores the address
  disable_ip_masking = false

  # decision: application-insights.networking.public_network_access - both bools, module default true
  internet_ingestion_enabled = false
  internet_query_enabled     = false
  monitor_private_link_scope = {
    scope = { resource_id = var.monitor_private_link_scope_id }
  }

  # decision: application-insights.security.local_authentication_disabled - module default false
  local_authentication_disabled = true

  retention_in_days = var.workspace_retention_days # follows the workspace

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.insights.resource_id }
output "connection_string" {
  value     = module.insights.connection_string
  sensitive = true
}
```

Output names and the `monitor_private_link_scope` member names are read from the README of the
pinned version. The connection string is an output for the application's app setting, marked
sensitive; with local authentication off it is not on its own a credential.

### Tests

With `azapi` mocked, the module's `resource` output is the component's `azapi_resource`, so
asserts target `body.properties.*` at plan time (`publicNetworkAccessForIngestion`,
`publicNetworkAccessForQuery`, `DisableLocalAuth`, `DisableIpMasking`, `SamplingPercentage`,
`WorkspaceResourceId`) - the exact paths read off a first `terraform test` run on the pinned
version. The scope membership and the role assignments are `# not-testable:` where the plan
hides them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
