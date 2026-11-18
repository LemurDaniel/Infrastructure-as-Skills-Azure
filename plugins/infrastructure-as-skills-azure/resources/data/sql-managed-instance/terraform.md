# Rendering an Azure SQL Managed Instance as Terraform

Mapping from the question set to the instance and its databases. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-sql-managedinstance/azurerm` | **v0.3.1** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random ~> 3.5`, and Terraform
`>= 1.9, < 2.0`. The root's provider set is the union with the other modules in the deployment.
The module builds the instance, its databases, the TDE protector, the private endpoints, the
threat-protection and classic vulnerability-assessment settings, role assignments and the
diagnostic setting; it also carries a failover group for a secondary. It builds **no** audit, no
NSG rule, and nothing inside a database.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
# The provider demands a SQL administrator even with Entra-only on: generated, never stored.
resource "random_password" "sqlmi_admin" {
  length  = 32
  special = true
}

module "sqlmi" {
  source  = "Azure/avm-res-sql-managedinstance/azurerm"
  version = "~> 0.3.0"

  name                = data.naming_name.sqlmi.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: sql-managed-instance.instance.service_tier / hardware_family
  sku_name = "GP_Gen5"
  # decision: sql-managed-instance.instance.vcores
  vcores = 4
  # decision: sql-managed-instance.instance.storage_gb
  storage_size_in_gb = 256
  # decision: sql-managed-instance.instance.license_type
  license_type = "LicenseIncluded"
  # decision: sql-managed-instance.instance.collation
  collation = "SQL_Latin1_General_CP1_CI_AS"
  # decision: sql-managed-instance.instance.timezone
  timezone_id = "UTC"
  # decision: sql-managed-instance.instance.maintenance_window
  maintenance_configuration_name = "SQL_WestEurope_MI_1"

  # decision: sql-managed-instance.resilience.zone_redundant - the module default is true
  zone_redundant_enabled = true

  # decision: sql-managed-instance.networking.subnet
  subnet_id = var.subnet_id
  # decision: sql-managed-instance.networking.public_data_endpoint
  public_data_endpoint_enabled = false
  # decision: sql-managed-instance.networking.connection_type - the module default is Default
  proxy_override = "Redirect"
  # decision: sql-managed-instance.networking.minimum_tls_version
  minimum_tls_version = "1.2"
  # decision: sql-managed-instance.networking.private_endpoint - none
  private_endpoints                       = {}
  private_endpoints_manage_dns_zone_group = false

  # decision: sql-managed-instance.identity.managed_identity
  managed_identities = { system_assigned = true }

  # decision: sql-managed-instance.identity.entra_admin / security.local_authentication_disabled
  active_directory_administrator = {
    login_username                      = var.entra_admin_login
    object_id                           = var.entra_admin_object_id
    principal_type                      = "Group"
    tenant_id                           = var.tenant_id
    azuread_authentication_only_enabled = true
  }
  # required by the provider; unusable while Entra-only is on
  administrator_login          = "sqlmiadmin"
  administrator_login_password = random_password.sqlmi_admin.result

  # decision: sql-managed-instance.security.threat_detection
  advanced_threat_protection_enabled = true
  # decision: sql-managed-instance.security.vulnerability_assessment - off: the classic form needs a storage account
  # (storage_account_resource_id and vulnerability_assessment when on)

  # decision: sql-managed-instance.data_protection.backup_storage_redundancy - the module default is GRS
  storage_account_type = "ZRS"

  # decision: sql-managed-instance.instance.databases
  databases = {
    app = {
      name = "app"
      # decision: sql-managed-instance.data_protection.short_term_retention_days
      short_term_retention_days = 7
      # decision: sql-managed-instance.data_protection.long_term_retention
      long_term_retention_policy = { weekly_retention = "P13W" }
    }
  }

  # decision: sql-managed-instance.observability.diagnostic_workspace / diagnostic_categories / metrics_enabled
  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["ResourceUsageStats", "SQLSecurityAuditEvents", "DevOpsOperationsAudit"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  # decision: sql-managed-instance.identity.role_assignments
  role_assignments = {}

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.sqlmi.resource_id }
```

Validated with `terraform validate` against v0.3.1 (azurerm 4.x). A customer-managed key adds
`transparent_data_encryption = { key_vault_key_id = var.cmk_key_id, auto_rotation_enabled = true }`
and `managed_identities = { user_assigned_resource_ids = [var.identity_id] }`; a private endpoint
replaces the empty map by `{ mi = { name = ..., subnet_resource_id = var.private_endpoint_subnet_id } }`.

### The public endpoint rule, the audit and the users

`enabled_with_firewall` is an `azurerm_network_security_rule` on the subnet's NSG (TCP 3342 from
`ip_rules` to the subnet), rendered only when this deployment owns the NSG; otherwise an open entry.

The audit and the logins are T-SQL, run as a member of the administrator group from inside the
network, after the apply:

```sql
CREATE SERVER AUDIT [audit] TO EXTERNAL_MONITOR;
CREATE SERVER AUDIT SPECIFICATION [audit-spec] FOR SERVER AUDIT [audit]
  ADD (SUCCESSFUL_LOGIN_GROUP), ADD (FAILED_LOGIN_GROUP), ADD (BATCH_COMPLETED_GROUP)
  WITH (STATE = ON);
ALTER SERVER AUDIT [audit] WITH (STATE = ON);

CREATE LOGIN [app-identity] FROM EXTERNAL PROVIDER;
```

followed by `CREATE USER ... FOR LOGIN` and `ALTER ROLE db_datareader ADD MEMBER` in each database.
The spec records `auditing_enabled` and `database_users` as that step.

### A second region

`geo_failover_region` is a second instance of this module in that region, created with
`dns_zone_partner_id = module.sqlmi.resource_id`, and `failover_group = { fog = { name, location,
partner_managed_instance_id, read_write_endpoint_failover_policy = { mode = "Automatic", grace_minutes = 60 } } }`
on the primary. The two subnets need connectivity (peering or a gateway) between them.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's `resource` output
(the `azurerm_mssql_managed_instance` attributes echoed from the inputs): `sku_name`, `vcores`,
`storage_size_in_gb`, `license_type`, `collation`, `timezone_id`, `zone_redundant_enabled`,
`subnet_id`, `public_data_endpoint_enabled`, `proxy_override`, `minimum_tls_version`,
`storage_account_type`, `maintenance_configuration_name`, the identity type and the
`azuread_administrator` block. The output paths are read off a first `terraform test` run on the
pinned version, not recalled. The databases, the threat-protection and TDE settings, the
diagnostic setting and any private endpoint are built in child resources whose bodies reach no
output: `# not-testable:` with that reason. `database_users`, `auditing_enabled`'s T-SQL half, the
NSG rule on a platform NSG and the Defender plan are `# not-testable:` (not a resource of this
plan). `random_password` is mocked like the platform.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the instance this
way, or a `GeoZone` backup answer. Targets `azurerm` **5.x**; check against
`terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
