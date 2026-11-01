# Rendering a Cosmos DB account as Terraform

Mapping from the question set to the account. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-documentdb-databaseaccount/azurerm` | **v0.11.0** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.11.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.6`,
`time ~> 0.12`, and Terraform `>= 1.9`. The root's provider set is the union with the other
modules in the deployment.

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
module "cosmos" {
  source  = "Azure/avm-res-documentdb-databaseaccount/azurerm"
  version = "~> 0.11.0"

  name                = data.naming_name.cosmos.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: cosmos-db.account.free_tier
  free_tier_enabled = false
  # decision: cosmos-db.account.total_throughput_limit
  capacity = { total_throughput_limit = -1 }

  # decision: cosmos-db.resilience.zone_redundant - the module default is true
  geo_locations = [
    { location = var.location, failover_priority = 0, zone_redundant = true },
  ]
  # decision: cosmos-db.resilience.automatic_failover
  automatic_failover_enabled = true
  # decision: cosmos-db.resilience.consistency_level - the module default is BoundedStaleness
  consistency_policy = { consistency_level = "Session" }

  # decision: cosmos-db.networking.public_network_access - a bool
  public_network_access_enabled         = false
  ip_range_filter                       = []
  network_acl_bypass_for_azure_services = false
  private_endpoints = {
    sql = {
      name               = data.naming_name.cosmos_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "Sql"
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: cosmos-db.security.local_authentication_disabled / key_based_metadata_writes
  local_authentication_disabled        = true
  access_key_metadata_writes_enabled   = false

  # decision: cosmos-db.data_protection.backup_policy
  backup = { type = "Continuous", tier = "Continuous7Days" }
  # decision: cosmos-db.data_protection.analytical_storage
  analytical_storage_enabled = false

  # decision: cosmos-db.containers.databases - the partition key is the application's
  sql_databases = {
    app = {
      name = "app"
      containers = {
        conversations = {
          name                = "conversations"
          partition_key_paths = ["/userId"]
          autoscale_settings  = { max_throughput = 1000 }
        }
      }
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["ControlPlaneRequests", "DataPlaneRequests"]
      log_groups            = []
      metric_categories     = ["Requests"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.cosmos.resource_id }
output "endpoint" { value = module.cosmos.endpoint }
```

### Data-plane roles

The module has **no input** for Cosmos DB's own role assignments. They are rendered next to it,
scoped to the account or to one database or container:

```hcl
resource "azurerm_cosmosdb_sql_role_assignment" "this" {
  for_each = var.data_plane_role_assignments

  resource_group_name = var.resource_group_name
  account_name        = data.naming_name.cosmos.name
  # 00000000-0000-0000-0000-000000000001 reader, ...0002 contributor (built-in)
  role_definition_id = "${module.cosmos.resource_id}/sqlRoleDefinitions/${each.value.role_definition_guid}"
  principal_id       = each.value.principal_id
  scope              = each.value.scope # the account id, or .../dbs/<db>[/colls/<c>]
}
```

Check the arguments against `terraform providers schema -json` for the `azurerm` the root
pins; the resource is `azurerm`'s, and it is the one place the module's provider constraint
(`~> 4.0`) is what makes it available.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the
consistency level, the public flag, local-authentication, the backup type, the geo locations'
zone redundancy, the capacity mode. The output paths are read off a first `terraform test` run
on the pinned version, not recalled. What the module builds in child resources - the private
endpoint, the diagnostic setting, role assignments, containers - is marked `# not-testable:`
with a reason where the plan hides it, as for storage.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the account
this way. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Resource and argument |
|---|---|
| the account | `azurerm_cosmosdb_account` (`kind = "GlobalDocumentDB"`, `offer_type = "Standard"`) |
