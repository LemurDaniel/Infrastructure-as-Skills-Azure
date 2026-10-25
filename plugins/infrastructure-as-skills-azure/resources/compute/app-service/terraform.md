# Rendering an App Service as Terraform

Mapping from the question set to the plan and the site. General layout, variables and
tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

Two modules, one per ARM resource, wired in the root:

| | Module | Documented against | Resolved |
|---|---|---|---|
| Plan | `Azure/avm-res-web-serverfarm/azurerm` | **v2.0.8** | 2026-10-18 |
| Site | `Azure/avm-res-web-site/azurerm` | **v0.24.1** | 2026-10-18 |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The plan module is `v2`, so
the pin is `~> 2.0`; the site module is `0.y` and the pin is `~> 0.24.0`.

**Both are AzAPI-based.** They take the resource group as `parent_id` (an id), require
`azapi ~> 2.12` (the site module; the plan module `~> 2.4`), `modtm ~> 0.3`, `random`
and `time`, and Terraform `>= 1.9`, and need no `azurerm` at all. They authenticate with
Entra ID. The root's provider set is the union with the other modules in the deployment.

### Decision → module input

| Decision | Module | Input | Note |
|---|---|---|---|
| `os_type` | plan, site | `os_type` | Both take it; `Linux` sets `reserved` |
| `sku` | plan | `sku_name` | Module default is **`P1v2`** - older hardware; must be written |
| `zone_redundant` | plan | `zone_balancing_enabled` | Module default is **`true`** - a Basic SKU with the default fails the plan; must be written |
| `instance_count` | plan | `worker_count` | Module default is **3**; must be written |
| `public_network_access` | site | `public_network_access_enabled` | **Bool** - `disabled` is `false`; not the 5.x string |
| `public_network_access` | site | `site_config.ip_restriction_default_action` | `Deny` unless `enabled`; module default `Allow` |
| `private_endpoint_subnet` | site | `private_endpoints = { sites = { subnet_resource_id } }` | `subresource_name` defaults to `sites` |
| `deployment.private_dns_records` | site | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `vnet_integration`, `integration_subnet` | site | `virtual_network_subnet_id` | Delegated subnet; see below |
| `vnet_route_all` | site | `vnet_route_all_traffic` | Module default `false`; the `site_config.vnet_route_all_enabled` form is older |
| `ip_restrictions` | site | `site_config.ip_restriction` and `scm_ip_restriction` | `scm_use_main_ip_restriction = true` instead of a second list |
| `managed_identity` | site | `managed_identities = { system_assigned, user_assigned_resource_ids }` | Module default `system_assigned = false`; written |
| `https_only` | site | `https_only` | Module default `true`; written anyway |
| `min_tls_version` | site | `site_config.minimum_tls_version`, `scm_minimum_tls_version` | Module default **`1.3`**; SCM `1.2` |
| `ftps_state` | site | `site_config.ftps_state` | Module default `FtpsOnly` |
| `basic_auth_enabled` | site | `ftp_publish_basic_authentication_enabled`, `scm_publish_basic_authentication_enabled` | SCM module default is **`true`** |
| `runtime_stack`, `runtime_version`, `container_image` | site | `site_config.application_stack` | One of `dotnet`, `node`, `python`, `java`, `php`, `docker` |
| `always_on` | site | `site_config.always_on` | |
| `health_check_path` | site | `site_config.health_check_path` | Omitted while empty |
| `http2_enabled` | site | `site_config.http2_enabled` | Module default `false` |
| `diagnostic_workspace`, `diagnostic_categories`, `metrics_enabled` | site | `diagnostic_settings = { workspace = { workspace_resource_id, logs = [{ category }], metrics = [{ category = "AllMetrics" }] } }` | Per-category, not `category_group` |
| `metrics_enabled` | plan | `diagnostic_settings` | The plan has metrics only |
| `deployment.module_telemetry` | both | `enable_telemetry` | |
| `context.tags` | both | `tags = local.tags` | |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "plan" {
  source  = "Azure/avm-res-web-serverfarm/azurerm"
  version = "~> 2.0"

  name      = data.naming_name.plan.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  os_type = "Linux"
  # decision: app-service.hosting.sku - the module default is P1v2
  sku_name = var.sku_name
  # decision: app-service.hosting.zone_redundant - the module default is true,
  # which a Basic size rejects
  zone_balancing_enabled = true
  # decision: app-service.hosting.instance_count - zone redundancy needs two or more
  worker_count = 2

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

module "app" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.24.0"

  name                     = data.naming_name.app.name
  location                 = var.location
  parent_id                = data.azurerm_resource_group.this.id
  kind                     = "webapp"
  os_type                  = "Linux"
  service_plan_resource_id = module.plan.resource_id

  # decision: app-service.networking.public_network_access - a bool on the module
  public_network_access_enabled = false

  # decision: app-service.networking.vnet_integration / integration_subnet
  virtual_network_subnet_id = var.integration_subnet_id
  # decision: app-service.networking.vnet_route_all
  vnet_route_all_traffic = true

  private_endpoints = {
    sites = {
      name               = data.naming_name.app_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities = { system_assigned = true }

  https_only = true
  # decision: app-service.security.basic_auth_enabled - the SCM default is true
  ftp_publish_basic_authentication_enabled = false
  scm_publish_basic_authentication_enabled = false

  site_config = {
    always_on                     = true
    http2_enabled                 = true
    ftps_state                    = "Disabled"
    minimum_tls_version           = "1.2"
    scm_minimum_tls_version       = "1.2"
    ip_restriction_default_action = "Deny"
    scm_use_main_ip_restriction   = true

    application_stack = {
      python = { python_version = "3.13" }
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs = [
        { category = "AppServiceHTTPLogs" },
        { category = "AppServiceAppLogs" },
        { category = "AppServiceAuditLogs" },
        { category = "AppServiceIPSecAuditLogs" },
        { category = "AppServicePlatformLogs" },
      ]
      metrics = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.app.resource_id }
output "default_hostname" { value = module.app.resource_uri }
```

**The integration subnet is delegated, and one plan owns it.** The subnet carries a
delegation to `Microsoft.Web/serverFarms`; for a referenced network it already exists,
for a created one the virtual-network call declares it with `delegation` and a /26. A
second plan in the same subnet fails at apply with an error about the delegation, not
about the plan.

**`public_network_access_enabled = false` and the private endpoint go together.** The
module already defaults the flag to `false`; written anyway. An app with the flag off and
no endpoint answers nobody, which is `disabled` working as stated.

### A shared plan

With `plan: shared` the instance has **no `module "plan"`** and none of `os_type`, `sku`,
`zone_redundant`, `instance_count`: they are the owner's. Its site takes the owner's plan id, and
the order is owner plan, then this site:

```hcl
module "web_mcp" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.24.0"

  # decision: app-service__mcp.hosting.plan - shared with app-service__web
  service_plan_resource_id = module.plan.resource_id
  # ... the site's own decisions, as above; virtual_network_subnet_id is the owner's
}
```

The private endpoint and the `privatelink.azurewebsites.net` record are per app; the zone is already
in `wiring.private_dns_zones` ([private-dns-zones.md](../../../core/iac-rendering/references/private-dns-zones.md)).
The assertions for the plan's decisions stay with the owner's file; this instance's tests assert
`service_plan_resource_id` and the site's own decisions.

### Tests

The site module's `resource` output is the `azapi_resource` of the site, so with `azapi`
and `modtm` mocked the asserts apply to `module.app.resource.body.properties.*` and are
known at plan time, as for the storage module
([avm.md](../../../core/iac-rendering/references/avm.md#tests-with-a-module-in-the-middle)).
The `resource` output is `sensitive`: a failing assert prints `(sensitive value)`, and the
error message states the expected value in words.

**The plan module exposes only `name` and `resource_id`.** No body reaches an output, so
`sku`, `zone_redundant`, `instance_count` and `os_type` on the plan are not observable
from the root; they carry `# not-testable: app-service.hosting.<key> - set through the
plan module's <input>; the module's own tests cover the mapping`. That is 3 of the 28
decisions. Read the call, not the plan, to check them.

```hcl
run "security" {
  command = plan

  # decision: app-service.security.https_only
  assert {
    condition     = module.app.resource.body.properties.httpsOnly == true
    error_message = "Plain HTTP is refused."
  }

  # decision: app-service.security.min_tls_version
  assert {
    condition     = module.app.resource.body.properties.siteConfig.minTlsVersion == "1.2"
    error_message = "TLS 1.2 is the floor; the module's own default is 1.3."
  }

  # decision: app-service.networking.public_network_access
  assert {
    condition     = module.app.resource.body.properties.publicNetworkAccess == "Disabled"
    error_message = "The app is private; its only way in is the private endpoint."
  }
}
```

The exact property paths under `body.properties.siteConfig` are read from the module's
plan on the pinned version, not recalled: run `terraform test` once with an assert
deliberately wrong and read the path off the failure.

## Authored rendering

The fallback - `implementation: authored`, a repository that already renders the app this
way, or reading what the modules do inside. Targets `azurerm` **5.x**.

| Decision | Argument |
|---|---|
| `os_type` | `azurerm_service_plan.os_type` and `azurerm_linux_web_app` / `azurerm_windows_web_app` (the resource type is the OS choice) |
| `sku` | `azurerm_service_plan.sku_name` |
| `zone_redundant` | `azurerm_service_plan.zone_balancing_enabled` |
| `instance_count` | `azurerm_service_plan.worker_count` |
| `public_network_access` | `public_network_access_enabled` (a bool, unchanged in 5.x; only storage moved to a string) |
| `vnet_integration` | `virtual_network_subnet_id` on the app, or `azurerm_app_service_virtual_network_swift_connection` (not both) |
| `vnet_route_all` | `vnet_route_all_enabled` in `site_config` |
| `https_only` | `https_only` |
| `min_tls_version` | `site_config.minimum_tls_version`, `scm_minimum_tls_version` |
| `ftps_state` | `site_config.ftps_state` |
| `basic_auth_enabled` | `ftp_publish_basic_authentication_enabled`, `webdeploy_publish_basic_authentication_enabled` (the SCM switch is the WebDeploy one on the provider) |
| `runtime_*` | `site_config.application_stack` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |

```hcl
resource "azurerm_service_plan" "this" {
  name                   = data.naming_name.plan.name
  resource_group_name    = var.resource_group_name
  location               = var.location
  os_type                = "Linux"
  sku_name               = var.sku_name
  zone_balancing_enabled = true
  worker_count           = 2
  tags                   = local.tags
}
```

Mixing the swift-connection resource with `virtual_network_subnet_id` on the app makes the
two fight on every apply - the same plan-churn bug as inline and standalone subnets.
Pick one.
