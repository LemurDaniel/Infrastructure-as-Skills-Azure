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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
