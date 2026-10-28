# Rendering Container Apps as Terraform

Mapping from the question set to the environment and the app. General layout, variables and
tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

Two modules, one per ARM resource, wired in the root:

| | Module | Documented against | Resolved |
|---|---|---|---|
| Environment | `Azure/avm-res-app-managedenvironment/azurerm` | **v0.5.1** | 2026-10-23 |
| App | `Azure/avm-res-app-containerapp/azurerm` | **v0.9.0** | 2026-10-23 |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pins are `~> 0.5.0` and
`~> 0.9.0`.

**Providers.** The environment module requires `azapi ~> 2.12` **and `azurerm ~> 4.0`** - a root
calling it cannot be on 5.x - plus `modtm`, `random`, Terraform `>= 1.10`; the app module is
AzAPI only (`azapi ~> 2.5`, Terraform `~> 1.11`). Both take the resource group by name
(`resource_group_name`; the environment also accepts `parent_id`, which wins). The root's
provider set is the union with the other modules.

### Decision -> module input

| Decision | Module | Input | Note |
|---|---|---|---|
| `workload_profile` | env | `workload_profiles = [{ name, workload_profile_type, minimum_count, maximum_count }]` | `Consumption` is a profile; the old singular `workload_profile` is deprecated |
| `workload_profile` | app | `workload_profile_name` | Unset: workload profiles are not used |
| `zone_redundant` | env | `zone_redundant` | Module default **`true`**; written. The old `zone_redundancy_enabled` is deprecated |
| `internal`, `infrastructure_subnet` | env | `vnet_configuration = { internal, infrastructure_subnet_id }` | The old `internal_load_balancer_enabled` and `infrastructure_subnet_id` are deprecated |
| `public_network_access` | env | `public_network_access` | `"Enabled"`/`"Disabled"`; **forced `Disabled` while `internal`** |
| `peer_traffic_encryption` | env | `peer_traffic_configuration = { encryption = { enabled } }` | Module default unset; written |
| `diagnostic_workspace` | env | `app_logs_configuration = { destination = "azure-monitor" }` | Omit it and app logs are off; **not** `log_analytics_workspace` (shared key) |
| `diagnostic_*`, `metrics_enabled` | env | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories, or every log is collected beside them |
| `container_image`, `container_size` | app | `template = { containers = [{ name, image, cpu, memory }] }` | cpu and memory are the pair, e.g. `0.5` and `"1Gi"` |
| `application_insights` | app | `template.containers[].env = [{ name = "APPLICATIONINSIGHTS_CONNECTION_STRING", value }, { name = "APPLICATIONINSIGHTS_AUTHENTICATION_STRING", value = "Authorization=AAD;ClientId=<client id>" }]` | The connection string as a plain value; the second while local auth is off, with the app's user-assigned identity; omitted while empty |
| `min_replicas`, `max_replicas` | app | `template.min_replicas`, `template.max_replicas` | |
| `revision_mode` | app | `revision_mode` | Default `Single`; written |
| `ingress`, `target_port`, `allow_insecure` | app | `ingress = { external_enabled, target_port, allow_insecure_connections, transport }` | **Omit `ingress` for `none`.** Module default `external_enabled = false`, insecure `false`; written |
| `managed_identity`, `user_assigned_identity_ids` | app | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| (the pull) | app | `registries = [{ server, identity }]` | `identity` is the user-assigned identity's resource id - never `username`/`password_secret_name` |
| `secret_references` | app | `secrets = { <k> = { name, key_vault_secret_id, identity } }` | Never `value` |
| `role_assignments` | app | `role_assignments` | |
| `deployment.module_telemetry` | both | `enable_telemetry` | |
| `context.tags` | both | `tags = local.tags` | |

### The call

```hcl
module "environment" {
  source  = "Azure/avm-res-app-managedenvironment/azurerm"
  version = "~> 0.5.0"

  name                = data.naming_name.environment.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: container-apps.environment.workload_profile
  workload_profiles = [
    { name = "Consumption", workload_profile_type = "Consumption" },
  ]
  # decision: container-apps.environment.zone_redundant - the module default is true
  zone_redundant = true
  # decision: container-apps.environment.internal / infrastructure_subnet
  vnet_configuration = {
    internal                 = true
    infrastructure_subnet_id = var.infrastructure_subnet_id
  }
  public_network_access = "Disabled"

  # decision: container-apps.environment.peer_traffic_encryption
  peer_traffic_configuration = { encryption = { enabled = true } }

  # logs through a diagnostic setting, not the workspace's shared key
  app_logs_configuration = { destination = "azure-monitor" }
  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["ContainerAppConsoleLogs", "ContainerAppSystemLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

module "app" {
  source  = "Azure/avm-res-app-containerapp/azurerm"
  version = "~> 0.9.0"

  name                                 = data.naming_name.app.name
  resource_group_name                  = var.resource_group_name
  container_app_environment_resource_id = module.environment.resource_id

  workload_profile_name = "Consumption"
  revision_mode         = "Single"

  template = {
    min_replicas = 2
    max_replicas = 10
    containers = [{
      name   = "app"
      image  = var.container_image # a tag or digest, never latest
      cpu    = 0.5
      memory = "1Gi"
      # decision: container-apps.observability.application_insights
      # not-testable: container-apps.observability.application_insights - the connection string is the component's output, known after apply
      env = [
        {
          name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
          value = var.application_insights_connection_string
        },
        {
          # local authentication is off on the component: the agent signs in with the app's identity
          name  = "APPLICATIONINSIGHTS_AUTHENTICATION_STRING"
          value = "Authorization=AAD;ClientId=${var.identity_client_id}"
        },
      ]
    }]
  }

  # decision: container-apps.ingress.* - the Bicep module defaults to external and HTTP
  ingress = {
    external_enabled           = false
    target_port                = var.target_port
    allow_insecure_connections = false
  }

  managed_identities = { user_assigned_resource_ids = [var.user_assigned_identity_id] }
  registries = [{
    server   = var.registry_login_server
    identity = var.user_assigned_identity_id
  }]
  secrets = {
    for k, v in var.secret_references : k => {
      name                = v.name
      key_vault_secret_id = v.key_vault_secret_url
      identity            = var.user_assigned_identity_id
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "app_id" { value = module.app.resource_id }
output "app_fqdn" { value = module.app.fqdn_url }
```

The member names of `template`, `ingress` and `registries`, and the output names, are read from
the README of the pinned version. The roles on the registry and the vault are granted before
either module is applied, outside these calls.

### Tests

With `azapi` and `modtm` mocked, the modules' `resource` outputs are `azapi_resource` bodies,
so asserts target the environment's and the app's `body.properties.*` at plan time
(`zoneRedundant`, `vnetConfiguration.internal`, `publicNetworkAccess`, the ingress block, the
replica bounds), as for the storage module
([avm.md](../../../core/iac-rendering/references/avm.md#tests-with-a-module-in-the-middle)).
The environment module also needs `azurerm` mocked. What the modules build in child resources -
the diagnostic setting, role assignments - is `# not-testable:` with a reason, and so is
`application_insights`: the connection string is the component's output, unknown until apply.
The exact paths are read off a first `terraform test` run on the pinned version.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource and argument |
|---|---|
| the environment | `azurerm_container_app_environment` (`zone_redundancy_enabled`, `infrastructure_subnet_id`, `internal_load_balancer_enabled`, `workload_profile`) |
| `peer_traffic_encryption` | not on `azurerm_container_app_environment` in 5.x (it has `mutual_tls_enabled` only): set `peerTrafficConfiguration` with an `azapi_update_resource` on the environment |
| `public_network_access` | `public_network_access` (a string, `Enabled` / `Disabled`) |
| the app | `azurerm_container_app` (`revision_mode`, `template`, `ingress`, `registry`, `secret`, `identity`) |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` on the environment |
