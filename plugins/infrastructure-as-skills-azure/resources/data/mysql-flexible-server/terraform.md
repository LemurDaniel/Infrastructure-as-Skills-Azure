# Rendering a MySQL Flexible Server as Terraform

Mapping from the question set to the server. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-dbformysql-flexibleserver/azurerm` | **v0.1.7** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.12`, `modtm ~> 0.3`, and Terraform
`>= 1.3.0, < 2.0`; the write-only password below needs Terraform **>= 1.11** in the root. The
root's provider set is the union with the other modules in the deployment. The module builds the
server, its databases, firewall rules, server parameters, the Entra administrator, private
endpoints, role assignments and the diagnostic setting. It does **not** build the
threat-protection setting or any database account.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs and inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| (no decision) | `storage.io_scaling_enabled`, `storage.iops` | Beside `size_gb` and `auto_grow_enabled` in the one `storage` object |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
# The administrator password MySQL demands at creation, though Entra-only never uses it: write-only,
# so it is in neither the state nor an output.
ephemeral "random_password" "bootstrap" {
  length = 32
}

module "mysql" {
  source  = "Azure/avm-res-dbformysql-flexibleserver/azurerm"
  version = "~> 0.1.0"

  name                = data.naming_name.mysql.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: mysql-flexible-server.server.mysql_version / compute_tier / sku_name
  mysql_version = "8.4"
  sku_name      = "GP_Standard_D2ds_v4"
  # decision: mysql-flexible-server.server.storage_size_gb / storage_auto_grow
  storage = {
    size_gb            = 64
    auto_grow_enabled  = true
    io_scaling_enabled = false
  }

  # decision: mysql-flexible-server.security.password_authentication_disabled
  # Entra-only (aad_auth_only below); the account MySQL requires is never used
  administrator_login               = "mysqladmin"
  administrator_password_wo         = ephemeral.random_password.bootstrap.result
  administrator_password_wo_version = 1

  # decision: mysql-flexible-server.identity.user_assigned_identity_ids / entra_admin
  managed_identities = { user_assigned_resource_ids = [var.user_assigned_identity_id] }
  active_directory_administrator = {
    identity_id = var.user_assigned_identity_id
    login       = var.entra_admin_name
    object_id   = var.entra_admin_object_id
    tenant_id   = var.tenant_id
  }

  # decision: mysql-flexible-server.resilience.high_availability - the module default is ZoneRedundant
  high_availability = { mode = "ZoneRedundant" }
  # decision: mysql-flexible-server.resilience.maintenance_window
  maintenance_window = { day_of_week = "0", start_hour = 2, start_minute = 0 }

  # decision: mysql-flexible-server.networking.public_network_access - a string
  public_network_access = "Disabled"
  firewall_rules        = {}
  private_endpoints = {
    mysql = {
      name               = data.naming_name.mysql_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "mysqlServer"
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: mysql-flexible-server.security.minimum_tls_version / password_authentication_disabled
  # decision: mysql-flexible-server.observability.audit_logging
  server_configuration = {
    aad_auth_only            = { name = "aad_auth_only", value = "ON" }
    tls_version              = { name = "tls_version", value = "TLSv1.2,TLSv1.3" }
    require_secure_transport = { name = "require_secure_transport", value = "ON" }
    audit_log_enabled        = { name = "audit_log_enabled", value = "ON" }
    audit_log_events         = { name = "audit_log_events", value = "CONNECTION" }
  }

  # decision: mysql-flexible-server.data_protection.backup_retention_days
  backup_retention_days = 7
  # decision: mysql-flexible-server.data_protection.geo_redundant_backup - the module default is true
  geo_redundant_backup_enabled = false

  # decision: mysql-flexible-server.server.databases
  databases = {
    app = { name = "app", charset = "utf8mb4", collation = "utf8mb4_0900_ai_ci" }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["MySqlAuditLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.mysql.resource_id }
output "fqdn" { value = module.mysql.resource_fqdn }
```

A burstable size sets `sku_name = "B_Standard_B2s"` and `high_availability = null`. A customer-managed
key adds `customer_managed_key = { key_vault_key_id, primary_user_assigned_identity_id }`; a
VNet-integrated server drops `private_endpoints` for `delegated_subnet_id` and `private_dns_zone_id`.
The Entra administrator is created after the server and its identity: the module waits on the
identity, and `active_directory_administrator_wait_seconds` lengthens the wait where the first apply
races it.

### Threat protection

The module has no input for the server-level setting; it is a child resource of the server:

```hcl
# decision: mysql-flexible-server.security.threat_protection
resource "azapi_resource" "threat_protection" {
  type      = "Microsoft.DBforMySQL/flexibleServers/advancedThreatProtectionSettings@2024-12-30"
  name      = "Default"
  parent_id = module.mysql.resource_id
  body = {
    properties = { state = "Enabled" }
  }
  schema_validation_enabled = false
}
```

The API version is the one the Bicep module of the same date uses. The Defender plan for open-source
relational databases is a subscription resource and the platform's.

### Database users

Entra users are created inside the server, as the Entra administrator:

```sql
CREATE AADUSER 'app-identity' IDENTIFIED BY 'a0000000-0000-0000-0000-000000000000';
GRANT SELECT ON app.* TO 'app-identity'@'%';
```

That is a step after the apply (the pipeline signs in as a member of the administrator group, or runs
a deployment script), not a Terraform resource; the spec records `database_users` as such.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the public
access string, the SKU, the high-availability mode, the backup retention and geo flag, the storage
block. The output paths are read off a first `terraform test` run on the pinned version, not recalled.
What the module builds in child resources - the private endpoint, the server parameters, the Entra
administrator, the diagnostic setting - is marked `# not-testable:` with a reason where the plan
hides it. `database_users` and the Defender plan are `# not-testable:` (not a resource of this plan).

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the server this way.
Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Resource and argument |
|---|---|
| the server | `azurerm_mysql_flexible_server` |
| (no decision) | `storage { io_scaling_enabled }` |
