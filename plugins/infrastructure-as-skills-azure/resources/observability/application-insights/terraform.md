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

| Decision | Input | Note |
|---|---|---|
| `workspace` | `workspace_id` | **Required** |
| `application_type` | `application_type` | Default `web`; written |
| `sampling_percentage` | `sampling_percentage` | Default 100; written |
| `daily_cap_gb` | `daily_data_cap_in_gb` | Module default **100**; `0` is unlimited; written |
| `store_client_ip` | `disable_ip_masking` | Same polarity: storing the address is disabling the masking (`true`); not storing is `false`, the default; written |
| `public_network_access` | `internet_ingestion_enabled`, `internet_query_enabled` | **Bools**; module defaults **`true`** for both; written |
| `private_link_scope` | `monitor_private_link_scope = { scope = { resource_id } }` | Adds the component to the platform's scope; member names from the README |
| `local_authentication_disabled` | `local_authentication_disabled` (same polarity - the module input, not the 5.x provider argument, which is the inverse `local_authentication_enabled`) | Module default **`false`**; written |
| `role_assignments` | `role_assignments` | |
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

| Decision | Argument on `azurerm_application_insights` |
|---|---|
| `workspace` | `workspace_id` (always; the classic form is not offered) |
| `application_type` | `application_type` |
| `sampling_percentage`, `daily_cap_gb` | `sampling_percentage`; `daily_data_cap_in_gb` |
| `store_client_ip` | `ip_masking_enabled` (**opposite polarity** to the AVM module's `disable_ip_masking`: storing the address is `ip_masking_enabled = false`) |
| `public_network_access` | `internet_ingestion_enabled`, `internet_query_enabled` |
| `local_authentication_disabled` | `local_authentication_enabled` (inverse; the 4.x `local_authentication_disabled` is gone in 5.x) |
| `private_link_scope` | `azurerm_monitor_private_link_scoped_service` |
