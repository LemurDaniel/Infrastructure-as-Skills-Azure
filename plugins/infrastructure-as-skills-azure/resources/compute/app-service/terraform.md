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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Setting | Module | Input | Note |
|---|---|---|---|
| `deployment.private_dns_records` | site | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
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

  # not-testable: app-service.runtime.container_image_owner - which image runs after the image pipeline is a property of the live site, not of the plan
  # decision: app-service.identity.entra_sign_in / entra_client_secret - none by default: no auth_settings_v2
  # decision: app-service.observability.application_insights
  # not-testable: app-service.observability.application_insights - the connection string is the component's output, known after apply
  application_insights_connection_string = var.application_insights_connection_string
  # local authentication is off on the component: the agent signs in with the app's identity
  app_settings = {
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING = "Authorization=AAD"
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

### Deployment slots

`deployment_slots` is a map on the site call, one entry per slot, key and `name` the slot's
name. **A slot inherits nothing from the site**: the slot submodule has its own defaults -
`public_network_access_enabled = false`, `minimum_tls_version = "1.3"`, `ftps_state =
"FtpsOnly"`, `http2_enabled = false`, `ip_restriction_default_action = "Allow"`, no identity,
and `docker_image_tag = "latest"` - so every site decision is written on each slot again,
from the same variables as the site. Checked against v0.24.1 (2026-10-27).

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

```hcl
  # decision: app-service.slots.deployment_slots
  deployment_slots = {
    test = {
      name                                     = "test"
      public_network_access_enabled            = false
      virtual_network_subnet_id                = var.integration_subnet_id
      vnet_route_all_traffic                   = true
      https_only                               = true
      ftp_publish_basic_authentication_enabled = false
      # the slot's SCM switch is the WebDeploy one
      webdeploy_publish_basic_authentication_enabled = false
      managed_identities = { user_assigned_resource_ids = [module.identity.resource_id] }

      # decision: app-service.slots.slot_access - same_as_app behind the entry
      private_endpoints = {
        sites = {
          name               = data.naming_name.app_slot_private_endpoint.name
          subnet_resource_id = var.private_endpoint_subnet_id
        }
      }

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
        # decision: app-service.slots.auto_swap - false, no auto_swap_slot_name
      }
    }
  }
```

The slot's ids are in `module.app.deployment_slots["<name>"].resource_id`. The slot
submodule exposes no body, so the slot's decisions are not observable from the root:
`deployment_slots` is asserted on the output's keys, the others carry
`# not-testable: app-service.slots.<key> - set on the slot submodule, which exposes only name and id`.

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
plan module's <input>; the module's own tests cover the mapping`. That is 3 of the 29
decisions. Read the call, not the plan, to check them. The fourth is `application_insights`:
the connection string is the component's output, unknown until apply, so the plan has no
value to compare.

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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

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
