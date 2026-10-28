# Rendering a Function App as Terraform

Mapping from the question set to the plan and the site. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
The two modules are the ones of the [App Service](../app-service/terraform.md) reference; read
it first, only what differs is here.

## With the AVM modules

| | Module | Documented against | Resolved |
|---|---|---|---|
| Plan | `Azure/avm-res-web-serverfarm/azurerm` | **v2.0.8** | 2026-10-23 |
| Site | `Azure/avm-res-web-site/azurerm` | **v0.24.1** | 2026-10-23 |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pins `~> 2.0` and `~> 0.24.0`.
Both are AzAPI-based and take the resource group as `parent_id`; the provider set is the one
of the App Service reference.

### Decision -> module input

| Decision | Module | Input | Note |
|---|---|---|---|
| `plan_type` | plan | `sku_name = "FC1"` / `"EP1"`..`"EP3"`, `os_type = "Linux"` | Flex is Linux only; Premium also `maximum_elastic_worker_count` and elastic scale |
| `plan_type` | site | `kind = "functionapp"`, `function_app_uses_fc1 = true` for Flex | |
| `runtime_stack`, `runtime_version` | site | `fc1_runtime_name`, `fc1_runtime_version` (Flex); `site_config.application_stack` (Premium) | The Flex stack names: `node`, `dotnet-isolated`, `powershell`, `python`, `java` |
| `zone_redundant` | plan | `zone_balancing_enabled` | Module default `true`; the plan module **fails early** in regions without `FCZONEREDUNDANCY` for FC1; written |
| `max_instance_count` | site | `maximum_instance_count` | Default `null` |
| `always_ready_instances` | site | `always_ready = { http = { instance_count } }` (Flex) | On Premium the plan's `worker_count` |
| `instance_memory_mb` | site | `instance_memory_in_mb` | Default 2048; written |
| `host_storage_account`, `host_storage_auth` | site | `storage_account_name`, `storage_uses_managed_identity = true`, `storage_user_assigned_identity_client_id` | Host connection (`AzureWebJobsStorage__accountName`, `__credential`, `__clientId`); **never** `storage_account_access_key` |
| `host_storage_auth`, `deployment_container` | site | `storage_authentication_type = "UserAssignedIdentity"`, `storage_user_assigned_identity_id`, `storage_container_endpoint` | **The second connection**, Flex only: the deployment package |
| `public_network_access` | site | `public_network_access_enabled` and `site_config.ip_restriction_default_action` | **Bool**; `Deny` unless `enabled` |
| `private_endpoint_subnet` | site | `private_endpoints = { sites = { subnet_resource_id } }` | |
| `deployment.private_dns_records` | site | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `vnet_integration`, `integration_subnet`, `vnet_route_all` | site | `virtual_network_subnet_id`, `vnet_route_all_traffic` | Delegation per plan; see `notes.md` |
| `ip_restrictions` | site | `site_config.ip_restriction`, `scm_ip_restriction` | `scm_use_main_ip_restriction = true` |
| `managed_identity`, `user_assigned_identity_ids` | site | `managed_identities = { user_assigned_resource_ids }`, `key_vault_reference_identity` | |
| `https_only`, `min_tls_version` | site | `https_only`, `site_config.minimum_tls_version`, `scm_minimum_tls_version` | Module TLS default is **1.3**; written |
| `basic_auth_enabled` | site | `ftp_publish_basic_authentication_enabled`, `scm_publish_basic_authentication_enabled` | SCM default is **true** |
| `application_insights` | site | `application_insights_connection_string`, and `app_settings.APPLICATIONINSIGHTS_AUTHENTICATION_STRING = "Authorization=AAD"` (`;ClientId=<client id>` user-assigned) while local auth is off | Omitted while empty |
| `diagnostic_*`, `metrics_enabled` | both | `diagnostic_settings = { workspace = { workspace_resource_id, logs, metrics } }` | The plan has metrics only |
| `deployment.module_telemetry` | both | `enable_telemetry` | |
| `context.tags` | both | `tags = local.tags` | |

### The call

```hcl
module "plan" {
  source  = "Azure/avm-res-web-serverfarm/azurerm"
  version = "~> 2.0"

  name      = data.naming_name.plan.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  os_type  = "Linux"
  sku_name = "FC1" # decision: function-app.hosting.plan_type
  # decision: function-app.hosting.zone_redundant - the module default is true, which a region
  # without FCZONEREDUNDANCY rejects for FC1
  zone_balancing_enabled = true

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "AllMetrics" }]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

module "function" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.24.0"

  name                     = data.naming_name.function.name
  location                 = var.location
  parent_id                = data.azurerm_resource_group.this.id
  kind                     = "functionapp"
  os_type                  = "Linux"
  service_plan_resource_id = module.plan.resource_id

  function_app_uses_fc1 = true
  fc1_runtime_name      = "python"
  fc1_runtime_version   = "3.12"
  # decision: function-app.hosting.max_instance_count / always_ready / instance_memory_mb
  maximum_instance_count = 20
  instance_memory_in_mb  = 2048
  always_ready           = { http = { instance_count = 1 } }

  # decision: function-app.storage.* - identity, never the storage key
  storage_account_name                     = var.host_storage_account_name
  storage_uses_managed_identity            = true
  storage_user_assigned_identity_client_id = var.identity_client_id
  # the second connection, Flex only: the deployment package
  storage_authentication_type        = "UserAssignedIdentity"
  storage_user_assigned_identity_id  = var.identity_id
  storage_container_endpoint         = "${var.host_storage_blob_endpoint}${var.deployment_container}"

  # decision: function-app.networking.public_network_access - a bool
  public_network_access_enabled = false
  virtual_network_subnet_id     = var.integration_subnet_id
  vnet_route_all_traffic        = true
  private_endpoints = {
    sites = {
      name               = data.naming_name.function_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities           = { user_assigned_resource_ids = [var.identity_id] }
  key_vault_reference_identity = var.identity_id

  https_only = true
  # decision: function-app.security.basic_auth_enabled - the SCM default is true
  ftp_publish_basic_authentication_enabled = false
  scm_publish_basic_authentication_enabled = false
  site_config = {
    minimum_tls_version           = "1.2"
    scm_minimum_tls_version       = "1.2"
    ip_restriction_default_action = "Deny"
    scm_use_main_ip_restriction   = true
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs = [
        { category = "FunctionAppLogs" },
        { category = "AppServiceAuditLogs" },
      ]
      metrics = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.function.resource_id }
```

The Flex and Premium inputs and the exact member names (`always_ready`, `site_config`) are read
from the README of the pinned version. The roles on the host storage account are granted before
the site is applied, outside these calls.

### Tests

As for the App Service: with `azapi` and `modtm` mocked, asserts target
`module.function.resource.body.properties.*` at plan time (`httpsOnly`, `publicNetworkAccess`,
`functionAppConfig.runtime`, `siteConfig.minTlsVersion`); the plan module exposes only `name` and
`resource_id`, so its decisions are `# not-testable:` with a reason. The paths are read off a first
`terraform test` run on the pinned version.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource |
|---|---|
| the plan | `azurerm_service_plan` (`sku_name = "FC1"` or `"EP1"`) |
| the Flex app | `azurerm_function_app_flex_consumption` (`runtime_name`, `runtime_version`, `storage_authentication_type`, `storage_container_endpoint`, `maximum_instance_count`, `instance_memory_in_mb`) |
| the Premium app | `azurerm_linux_function_app` (`storage_uses_managed_identity`, `storage_account_name`) |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
