# Rendering an AI Search service as Terraform

Mapping from the question set to the service. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-search-searchservice/azurerm` | **v0.3.0** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. `0.3` is early: the pin is
`~> 0.3.0` and a minor is expected to break.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random ~> 3.5`, and
Terraform `>= 1.9`. The root's provider set is the union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku` | Module default `standard`; written |
| `replica_count` | `replica_count` | Module default **1** (Bicep: 3); written |
| `partition_count` | `partition_count` | Default 1; written |
| `semantic_ranker` | `semantic_search_sku` | `free` / `standard`; `null` for `disabled` |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default **`true`** |
| `ip_rules` | `allowed_ips` | List of addresses or CIDR blocks |
| `network_rule_bypass` | `network_rule_bypass_option` | `None` / `AzureServices`; default `None`; written |
| `private_endpoint_subnet` | `private_endpoints = { search = { subnet_resource_id } }` | `subresource_name` defaults to `searchService` |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `role_assignments` | `role_assignments` | |
| `local_authentication_disabled` | `local_authentication_enabled` | **Inverse**; module default `null` (on); written |
| `cmk_enforcement` | `customer_managed_key_enforcement_enabled` | Default `null` (false); written |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories, or every log is collected beside them |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "search" {
  source  = "Azure/avm-res-search-searchservice/azurerm"
  version = "~> 0.3.0"

  name                = data.naming_name.search.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: search-service.service.sku
  sku = "standard"
  # decision: search-service.service.replica_count - the module default is 1
  replica_count = 2
  partition_count = 1
  semantic_search_sku = "free"

  # decision: search-service.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  allowed_ips                   = []
  network_rule_bypass_option    = "None"
  private_endpoints = {
    search = {
      name               = data.naming_name.search_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities = { system_assigned = true }

  # decision: search-service.security.local_authentication_disabled - inverse input
  local_authentication_enabled = false

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["OperationLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.search.resource_id }
```

Output names and the exact `logs`/`private_endpoints` member names are read from the README of
the pinned version.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the SKU,
the replica and partition counts, the public flag, local authentication, the semantic SKU. The
output paths are read off a first `terraform test` run on the pinned version. What the module
builds in child resources - the endpoint, the diagnostic setting, role assignments - is marked
`# not-testable:` with a reason where the plan hides it.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_search_service` |
|---|---|
| `sku` | `sku` |
| `replica_count`, `partition_count` | `replica_count`, `partition_count` |
| `semantic_ranker` | `semantic_search_sku` |
| `public_network_access` | `public_network_access_enabled`, `allowed_ips` |
| `network_rule_bypass` | `network_rule_bypass_option` |
| `managed_identity` | `identity { type }` |
| `local_authentication_disabled` | `local_authentication_enabled` (inverse) |
| `cmk_enforcement` | `customer_managed_key_enforcement_enabled` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
