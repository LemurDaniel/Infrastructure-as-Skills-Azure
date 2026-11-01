# Rendering an Azure SQL Database server as Terraform

Mapping from the question set to the server and its databases. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-sql-server/azurerm` | **v0.2.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.26` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, and Terraform
`>= 1.9, < 2.0`. The root's provider set is the union with the other modules in the deployment.
The module builds the server, its databases and elastic pools, firewall rules, private endpoints,
role assignments and the database diagnostic settings. It does **not** build the server audit,
the server security alert policy, or anything inside a database.

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
module "sql" {
  source  = "Azure/avm-res-sql-server/azurerm"
  version = "~> 0.2.0"

  name                = data.naming_name.sql.name
  location            = var.location
  resource_group_name = var.resource_group_name
  server_version      = "12.0"

  # decision: sql-database.security.local_authentication_disabled / identity.entra_admin
  # Entra-only: no administrator_login, no password
  azuread_administrator = {
    azuread_authentication_only = true
    login_username              = var.entra_admin_login
    object_id                   = var.entra_admin_object_id
    tenant_id                   = var.tenant_id
  }

  # decision: sql-database.networking.public_network_access - a bool
  public_network_access_enabled = false
  firewall_rules                = {}
  private_endpoints = {
    sql = {
      name               = data.naming_name.sql_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "sqlServer"
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: sql-database.identity.managed_identity
  managed_identities = { system_assigned = true }

  # decision: sql-database.security.vulnerability_assessment
  express_vulnerability_assessment_enabled = true

  # decision: sql-database.database.databases - sizes and tiers are the application's
  databases = {
    app = {
      name = "app"
      # decision: sql-database.database.service_tier / compute_tier / vcores
      sku_name = "GP_Gen5_2"
      # decision: sql-database.database.collation
      collation = "SQL_Latin1_General_CP1_CI_AS"
      # decision: sql-database.database.max_size_gb
      max_size_gb = 32
      # decision: sql-database.resilience.zone_redundant
      zone_redundant = true
      # decision: sql-database.data_protection.backup_storage_redundancy - the module default is Geo
      storage_account_type = "Zone"
      # decision: sql-database.security.key_management - TDE stays on
      transparent_data_encryption_enabled = true
      # decision: sql-database.data_protection.short_term_retention_days
      short_term_retention_policy = { retention_days = 7, backup_interval_in_hours = 12 }
      # decision: sql-database.data_protection.long_term_retention
      long_term_retention_policy = { weekly_retention = "P13W" }

      diagnostic_settings = {
        workspace = {
          workspace_resource_id = var.diagnostic_workspace_id
          log_categories        = ["Errors", "Timeouts", "Blocks", "Deadlocks"]
          log_groups            = []
          metric_categories     = ["Basic"]
        }
      }
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.sql.resource_id }
output "name" { value = module.sql.resource_name }
```

A serverless database replaces the three size lines by
`sku_name = "GP_S_Gen5_2"`, `min_capacity = 0.5`, `auto_pause_delay_in_minutes = 60`; a pooled one
takes `sku_name = "ElasticPool"` and `elastic_pool_key = "<pool>"`.

### Audit, threat detection and the audit diagnostic

Neither is in the module, and the audit needs two pieces - the policy and the diagnostic setting
on `master` - or it records nothing:

```hcl
# decision: sql-database.observability.auditing_enabled
resource "azurerm_mssql_server_extended_auditing_policy" "this" {
  server_id              = module.sql.resource_id
  log_monitoring_enabled = true
}

resource "azurerm_monitor_diagnostic_setting" "audit" {
  name                       = "audit"
  target_resource_id         = "${module.sql.resource_id}/databases/master"
  log_analytics_workspace_id = var.diagnostic_workspace_id

  enabled_log {
    category = "SQLSecurityAuditEvents"
  }

  depends_on = [azurerm_mssql_server_extended_auditing_policy.this]
}

# decision: sql-database.security.threat_detection
resource "azurerm_mssql_server_security_alert_policy" "this" {
  resource_group_name = var.resource_group_name
  server_name         = module.sql.resource_name
  state               = "Enabled"
}
```

Check the arguments against `terraform providers schema -json` for the `azurerm` the root pins. The
Defender for SQL plan is a subscription resource and the platform's; the policy above does not enable
it.

### Database users

Entra users are created in each database as the Entra administrator, with T-SQL:

```sql
CREATE USER [app-identity] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [app-identity];
```

That is a step after the apply (the pipeline signs in as the administrator group's member, or runs a
deployment script), not a Terraform resource; the spec records `database_users` as such.

### A second region

`geo_failover_region` is a second instance of this module in that region and an
`azurerm_mssql_failover_group` binding the two servers' databases. The module has no input for
either; they are rendered next to it.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the public flag,
the Entra-only block, the minimum TLS version, the databases' `sku_name`, zone redundancy, storage
account type and retention. The output paths are read off a first `terraform test` run on the pinned
version, not recalled. What the module builds in child resources - the private endpoint, firewall
rules, diagnostic settings - is marked `# not-testable:` with a reason where the plan hides it.
`database_users` and the Defender plan are `# not-testable:` (not a resource of this plan).

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the server this way.
Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Resource and argument |
|---|---|
| the server | `azurerm_mssql_server` (`version = "12.0"`) |
