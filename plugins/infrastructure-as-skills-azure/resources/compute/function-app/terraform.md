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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Setting | Module | Input | Note |
|---|---|---|---|
| `deployment.private_dns_records` | site | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
