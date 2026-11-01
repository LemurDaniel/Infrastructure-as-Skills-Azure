# Rendering a PostgreSQL Flexible Server as Terraform

Mapping from the question set to the server. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-dbforpostgresql-flexibleserver/azurerm` | **v0.2.3** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.12` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, and Terraform
`>= 1.9, < 2.0`. The root's provider set is the union with the other modules in the deployment.
The module builds the server, its databases, firewall rules, configurations, the Entra
administrators, private endpoints, role assignments and the diagnostic setting. It does **not**
build the threat-protection setting or any database role.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `postgres_version` | `server_version` | A string (`"17"`); the module's description lists up to `16` - check the provider |
| `compute_tier`, `sku_name` | `sku_name = "GP_Standard_D2ds_v5"` | The tier is the **prefix** (`B_`, `GP_`, `MO_`) |
| `storage_size_gb` | `storage_mb` | **Megabytes** (`131072`); only the values the provider lists |
| `storage_auto_grow` | `auto_grow_enabled` | Default null; written |
| `databases` | `databases = { <key> = { name, charset, collation } }` | |
| `high_availability` | `high_availability = { mode = "ZoneRedundant" }`, or `null` for `disabled` | Module default **`ZoneRedundant`**; written. `null` on burstable compute |
| `maintenance_window` | `maintenance_window = { day_of_week, start_hour, start_minute }` | `day_of_week` a string, `"0"` Sunday; module default 00:00 |
| `private_connectivity: private_endpoint` | `private_endpoints`, with `delegated_subnet_id` and `private_dns_zone_id` unset | Fixed at creation, either way - the network mode (notes.md) |
| `private_connectivity: vnet_integration` | `delegated_subnet_id`, `private_dns_zone_id` | Fixed at creation, either way - the network mode (notes.md) |
| `public_network_access` | `public_network_access_enabled` | **Bool**, default `false`; written |
| `ip_rules`, `allow_azure_services` | `firewall_rules = { <key> = { name, start_ip_address, end_ip_address } }` | **Module default is a rule that admits `0.0.0.0` - `255.255.255.255`: `firewall_rules = {}` is written on every call** |
| `private_endpoint_subnet` | `private_endpoints = { pg = { subnet_resource_id, subresource_name = "postgresqlServer" } }` | |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `entra_admins` | `ad_administrator = { <key> = { object_id, principal_name, principal_type, tenant_id } }` | |
| `password_authentication_disabled` | `authentication = { active_directory_auth_enabled = true, password_auth_enabled = false, tenant_id }` and **no** `administrator_login`/`administrator_password` | Module default is null, the provider's: password on |
| `database_roles` | **not the module** | SQL after the deployment |
| `role_assignments` | `role_assignments` | Control plane |
| `minimum_tls_version` | `server_configuration = { ssl_min_protocol_version = { name, config }, require_secure_transport = { name, config } }` | |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_key_id, primary_user_assigned_identity_id }` | Versionless key id; the geo-backup key is a second pair |
| `threat_protection` | **not the module** - an `azapi_resource` child | |
| `backup_retention_days` | `backup_retention_days` | |
| `geo_redundant_backup` | `geo_redundant_backup_enabled` | Default null (the provider's `false`); written |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups, metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "postgresql" {
  source  = "Azure/avm-res-dbforpostgresql-flexibleserver/azurerm"
  version = "~> 0.2.0"

  name                = data.naming_name.postgresql.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: postgresql-flexible-server.server.postgres_version / compute_tier / sku_name
  server_version = "17"
  sku_name       = "GP_Standard_D2ds_v5"
  # decision: postgresql-flexible-server.server.storage_size_gb / storage_auto_grow
  storage_mb        = 131072
  auto_grow_enabled = true

  # decision: postgresql-flexible-server.security.password_authentication_disabled
  # Entra-only: no administrator_login, no password
  authentication = {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = var.tenant_id
  }
  # decision: postgresql-flexible-server.identity.entra_admins
  ad_administrator = {
    admins = {
      tenant_id      = var.tenant_id
      object_id      = var.entra_admin_object_id
      principal_name = var.entra_admin_name
      principal_type = "Group"
    }
  }

  # decision: postgresql-flexible-server.resilience.high_availability - the module default is ZoneRedundant
  high_availability = { mode = "ZoneRedundant" }
  # decision: postgresql-flexible-server.resilience.maintenance_window
  maintenance_window = { day_of_week = "0", start_hour = 2, start_minute = 0 }

  # decision: postgresql-flexible-server.networking.public_network_access - a bool
  public_network_access_enabled = false
  # the module's default firewall admits every address: written empty
  firewall_rules = {}
  private_endpoints = {
    pg = {
      name               = data.naming_name.postgresql_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "postgresqlServer"
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: postgresql-flexible-server.security.minimum_tls_version
  server_configuration = {
    ssl_min_protocol_version = { name = "ssl_min_protocol_version", config = "TLSv1.2" }
    require_secure_transport = { name = "require_secure_transport", config = "on" }
  }

  # decision: postgresql-flexible-server.data_protection.backup_retention_days
  backup_retention_days = 7
  # decision: postgresql-flexible-server.data_protection.geo_redundant_backup
  geo_redundant_backup_enabled = false

  # decision: postgresql-flexible-server.server.databases
  databases = {
    app = { name = "app", charset = "UTF8", collation = "en_US.utf8" }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["PostgreSQLLogs", "PostgreSQLFlexSessions"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.postgresql.resource_id }
output "fqdn" { value = module.postgresql.fqdn }
```

A burstable size sets `sku_name = "B_Standard_B2s"` and `high_availability = null`. A customer-managed key
adds `customer_managed_key = { key_vault_key_id, primary_user_assigned_identity_id }` and the
user-assigned identity; a VNet-integrated server drops `private_endpoints` for `delegated_subnet_id`
and `private_dns_zone_id`.

### Threat protection

The module has no input for the server-level setting; it is a child resource of the server:

```hcl
# decision: postgresql-flexible-server.security.threat_protection
resource "azapi_resource" "threat_protection" {
  type      = "Microsoft.DBforPostgreSQL/flexibleServers/advancedThreatProtectionSettings@2026-01-01-preview"
  name      = "Default"
  parent_id = module.postgresql.resource_id
  body = {
    properties = { state = "Enabled" }
  }
  schema_validation_enabled = false
}
```

The API version is the one the Bicep module of the same date uses; it is read from the module
source again before a render. The Defender plan for open-source relational databases is a
subscription resource and the platform's.

### Database roles

Entra roles are created inside the server, as the Entra administrator:

```sql
SELECT * FROM pgaadauth_create_principal('app-identity', false, false);
GRANT CONNECT ON DATABASE app TO "app-identity";
```

That is a step after the apply (the pipeline signs in as a member of the administrator group, or
runs a deployment script), not a Terraform resource; the spec records `database_roles` as such.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the public
flag, the authentication block, the SKU, the high-availability mode, the backup retention and geo
flag, the storage size. The output paths are read off a first `terraform test` run on the pinned
version, not recalled. What the module builds in child resources - the private endpoint, the
configurations, the Entra administrators, the diagnostic setting - is marked `# not-testable:`
with a reason where the plan hides it. `database_roles` and the Defender plan are
`# not-testable:` (not a resource of this plan).

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the server this way.
Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource and argument |
|---|---|
| the server | `azurerm_postgresql_flexible_server` |
| `postgres_version`, `sku_name`, `storage_size_gb`, `storage_auto_grow` | `version`, `sku_name`, `storage_mb`, `auto_grow_enabled` |
| `high_availability`, `maintenance_window` | `high_availability { mode }`, `maintenance_window { day_of_week, start_hour, start_minute }` |
| `public_network_access` | `public_network_access_enabled`, `azurerm_postgresql_flexible_server_firewall_rule` |
| `private_connectivity: vnet_integration` | `delegated_subnet_id`, `private_dns_zone_id` |
| `private_connectivity: private_endpoint` | `azurerm_private_endpoint` with `subresource_names = ["postgresqlServer"]` |
| `password_authentication_disabled` | `authentication { active_directory_auth_enabled, password_auth_enabled, tenant_id }` |
| `entra_admins` | `azurerm_postgresql_flexible_server_active_directory_administrator` |
| `minimum_tls_version` | `azurerm_postgresql_flexible_server_configuration` |
| `key_management` | `customer_managed_key { key_vault_key_id, primary_user_assigned_identity_id }` |
| `backup_retention_days`, `geo_redundant_backup` | `backup_retention_days`, `geo_redundant_backup_enabled` |
| `databases` | `azurerm_postgresql_flexible_server_database` |
| `threat_protection` | `azapi_resource` `advancedThreatProtectionSettings` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
