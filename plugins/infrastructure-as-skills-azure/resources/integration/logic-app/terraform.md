# Rendering Logic Apps as Terraform

Mapping from the question set to the resources. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
`hosting` picks the modules: Standard is the plan and site modules of the
[App Service](../../compute/app-service/terraform.md) and [Function App](../../compute/function-app/terraform.md)
references with a logic-app kind; Consumption is the workflow module.

## With the AVM modules

| | Module | Documented against | Resolved | Status |
|---|---|---|---|---|
| Standard plan | `Azure/avm-res-web-serverfarm/azurerm` | **v2.0.8** | 2026-10-26 | Available |
| Standard site | `Azure/avm-res-web-site/azurerm` | **v0.24.1** | 2026-10-26 | Available |
| Consumption workflow | `Azure/avm-res-logic-workflow/azurerm` | **v0.1.2** | 2026-10-26 | Available |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pins `~> 2.0`, `~> 0.24.0`,
`~> 0.1.0`.

**Provider requirements.** The plan and site modules are AzAPI-based (`parent_id`, `azapi ~> 2.12`,
`modtm ~> 0.3`, `random`, `time >= 0.9` for the site, Terraform `>= 1.9`) and need no `azurerm`.
The workflow module is **`azurerm`-based with `azurerm >= 4.21.1, < 5.0`** (plus `azapi ~> 2.0`,
`modtm`, `random`) and takes `resource_group_name` **and** `resource_group_id` - so a root that
renders a Consumption workflow cannot be on `azurerm` 5.x. A Standard-only root may be on 5.x.

### Decision -> module input

| Decision | Module | Input | Note |
|---|---|---|---|
| `hosting: standard` | site | `kind = "logicapp"`, `os_type = "Windows"` | The module maps `logicapp` + Windows to the ARM kind `functionapp,workflowapp` |
| `hosting: consumption` | workflow | the module itself | One module call per `workflows` entry |
| `plan: shared`, `shared_plan_with` | site | `service_plan_resource_id` = the owner's plan id; no plan module | |
| `plan_sku` | plan | `sku_name = "WS1"` | Module default **`P1v2`**, which a logic app refuses; written |
| `zone_redundant` | plan | `zone_balancing_enabled` | Module default `true`; written. The minimum instance count for a zone-redundant WS plan is read from the documentation |
| `instance_count` | plan | `worker_count` | |
| `max_instance_count` | plan | `maximum_elastic_worker_count` | |
| `workflows` | site | - (content, deployed from the repository) | `# not-testable:` on Standard |
| `state` | workflow | `state` | Default `"Enabled"`; written |
| `trigger_authentication` | workflow | `access_control = { triggers = { openAuthenticationPolicies = {...}, allowedCallerIpAddresses = [...] } }` | Untyped map in ARM spelling; the SAS switch's property name is checked before a render |
| `trigger_authentication` | site | `auth_settings_v2` | Easy Auth in front of the request triggers |
| `host_storage_account` | site | `storage_account_name` | **Required by the module for `logicapp`** |
| `host_storage_auth` | site | **`identity` is not carried by the module** for a logic app: its logic-app settings always write `AzureWebJobsStorage` as a connection string with the account key, merged *after* `app_settings` and without the override guard the function-app settings have, and `storage_account_access_key` is validated non-null for `kind = "logicapp"`. `identity` renders the site **authored** (`azapi_resource`, below) and the spec records `implementation: authored` with `source: { forced_by: avm-res-web-site v0.24.1 writes the storage key for a logic app }`. `key` renders the module with `storage_account_access_key = data.azurerm_key_vault_secret.host_storage_key.value` and `storage_account_share_name` | Re-read the pinned README's logic-app settings before a render; the module may gain the identity path |
| `public_network_access` | site | `public_network_access_enabled` (bool), `site_config.ip_restriction_default_action` | Module default `false`; written |
| `public_network_access` | workflow | `access_control.triggers.allowedCallerIpAddresses` | No `disabled` exists |
| `allowed_caller_ip_ranges` | site / workflow | `site_config.ip_restriction` / `access_control.triggers.allowedCallerIpAddresses[].addressRange` | |
| `private_endpoint_subnet` | site | `private_endpoints = { sites = { subnet_resource_id } }` | |
| `deployment.private_dns_records` | site | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `vnet_integration`, `integration_subnet`, `vnet_route_all` | site | `virtual_network_subnet_id`, `vnet_route_all_traffic` | |
| `managed_identity`, `user_assigned_identity_ids` | site / workflow | `managed_identities = { user_assigned_resource_ids }`, site also `key_vault_reference_identity` | |
| `role_assignments` | site / workflow | `role_assignments` | |
| `https_only` | site | `https_only` | |
| `min_tls_version` | site | `site_config.minimum_tls_version`, `scm_minimum_tls_version` | Module default **1.3**; written |
| `basic_auth_enabled` | site | `ftp_publish_basic_authentication_enabled`, `scm_publish_basic_authentication_enabled` | SCM default **true** |
| `application_insights` | site | `APPLICATIONINSIGHTS_CONNECTION_STRING` in `app_settings` | Omitted while empty |
| `diagnostic_*`, `metrics_enabled` | site / plan | `diagnostic_settings = { workspace = { workspace_resource_id, logs = [{ category }], metrics = [{ category }] } }` | The older object form; the plan has metrics only |
| `diagnostic_*`, `metrics_enabled` | workflow | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories } }` | `log_groups` defaults to `["allLogs"]`; set empty |
| `deployment.module_telemetry` | all | `enable_telemetry` | |
| `context.tags` | all | `tags = local.tags` | |

### The call - Standard

```hcl
module "logic_plan" {
  source  = "Azure/avm-res-web-serverfarm/azurerm"
  version = "~> 2.0"

  name      = data.naming_name.logic_plan.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  os_type  = "Windows"
  sku_name = "WS1" # decision: logic-app.hosting.plan_sku - the module default P1v2 is not a workflow plan
  # decision: logic-app.hosting.zone_redundant, instance_count, max_instance_count
  zone_balancing_enabled       = true
  worker_count                 = 2
  maximum_elastic_worker_count = 20

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "AllMetrics" }]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

module "logic_app" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.24.0"

  name                     = data.naming_name.logic_app.name
  location                 = var.location
  parent_id                = data.azurerm_resource_group.this.id
  kind                     = "logicapp" # decision: logic-app.hosting.hosting - rendered as functionapp,workflowapp
  os_type                  = "Windows"
  service_plan_resource_id = module.logic_plan.resource_id

  # decision: logic-app.storage.host_storage_account, host_storage_auth: key - the module composes
  # the connection strings from the key; the key is read from the vault, never written in the root
  storage_account_name       = var.host_storage_account_name
  storage_account_access_key = data.azurerm_key_vault_secret.host_storage_key.value
  storage_account_share_name = data.naming_name.logic_app.name
  app_settings = {
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.application_insights_connection_string
  }

  # decision: logic-app.networking.public_network_access - a bool
  public_network_access_enabled = false
  virtual_network_subnet_id     = var.integration_subnet_id
  vnet_route_all_traffic        = true
  private_endpoints = {
    sites = {
      name               = data.naming_name.logic_app_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities           = { user_assigned_resource_ids = [var.identity_id] }
  key_vault_reference_identity = var.identity_id

  https_only = true
  # decision: logic-app.security.basic_auth_enabled - the SCM default is true
  ftp_publish_basic_authentication_enabled = false
  scm_publish_basic_authentication_enabled = false
  site_config = {
    minimum_tls_version           = "1.2" # decision: logic-app.security.min_tls_version - module default 1.3
    scm_minimum_tls_version       = "1.2"
    ip_restriction_default_action = "Deny"
    scm_use_main_ip_restriction   = true
  }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
      principal_type             = v.principal_type
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs                  = [{ category = "WorkflowRuntime" }]
      metrics               = [{ category = "AllMetrics" }]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.logic_app.resource_id }
```

`data.azurerm_key_vault_secret.host_storage_key` reads the storage account key the storage set's
render wrote to the vault; it is `sensitive` in state. The roles of the identity on the host storage
account are granted before the site is applied, outside this call.

### The call - Standard with identity-based host storage (authored site)

`host_storage_auth: identity` is the guardrail default and the module cannot render it, so the
site is an `azapi_resource` beside the plan module, with the host settings the Bicep reference
lists written through a `config/appsettings` child:

```hcl
resource "azapi_resource" "logic_app" {
  type      = "Microsoft.Web/sites@2024-04-01"
  name      = data.naming_name.logic_app.name
  parent_id = data.azurerm_resource_group.this.id
  location  = var.location
  tags      = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  body = {
    kind = "functionapp,workflowapp" # decision: logic-app.hosting.hosting
    properties = {
      serverFarmId              = module.logic_plan.resource_id
      httpsOnly                 = true  # decision: logic-app.security.https_only
      publicNetworkAccess       = "Disabled" # decision: logic-app.networking.public_network_access
      virtualNetworkSubnetId    = var.integration_subnet_id
      vnetRouteAllEnabled       = true
      keyVaultReferenceIdentity = var.identity_id
      siteConfig = {
        minTlsVersion                       = "1.2" # decision: logic-app.security.min_tls_version
        scmMinTlsVersion                    = "1.2"
        ftpsState                           = "Disabled"
        ipSecurityRestrictionsDefaultAction = "Deny"
        scmIpSecurityRestrictionsUseMain    = true
        netFrameworkVersion                 = "v8.0"
      }
    }
  }
}

resource "azapi_resource" "logic_app_settings" {
  type      = "Microsoft.Web/sites/config@2024-04-01"
  name      = "appsettings"
  parent_id = azapi_resource.logic_app.id

  body = {
    properties = {
      FUNCTIONS_EXTENSION_VERSION                     = "~4"
      FUNCTIONS_WORKER_RUNTIME                        = "dotnet"
      WEBSITE_NODE_DEFAULT_VERSION                    = "~22"
      AzureFunctionsJobHost__extensionBundle__id      = "Microsoft.Azure.Functions.ExtensionBundle.Workflows"
      AzureFunctionsJobHost__extensionBundle__version = "[1.*, 2.0.0)"
      # decision: logic-app.storage.host_storage_auth - identity for blob, queue and table
      AzureWebJobsStorage__accountName = var.host_storage_account_name
      AzureWebJobsStorage__credential  = "managedidentity"
      AzureWebJobsStorage__clientId    = var.identity_client_id
      # the content share: the one setting that takes a connection string, as a Key Vault reference
      WEBSITE_CONTENTAZUREFILECONNECTIONSTRING = var.content_share_connection_kv_reference
      WEBSITE_CONTENTSHARE                     = data.naming_name.logic_app.name
      APPLICATIONINSIGHTS_CONNECTION_STRING    = var.application_insights_connection_string
    }
  }
}
```

The private endpoint, the basic-auth policies, the role assignments and the diagnostic setting
are then the authored resources of the table at the end. `var.content_share_connection_kv_reference`
is `@Microsoft.KeyVault(SecretUri=<secret>)` for the connection-string secret the storage set's
render wrote, resolved through `keyVaultReferenceIdentity`. The API version is one `az provider
show -n Microsoft.Web` lists and the pinned `azapi` knows.

### The call - Consumption

```hcl
module "workflow" {
  for_each = toset(var.workflows)

  source  = "Azure/avm-res-logic-workflow/azurerm"
  version = "~> 0.1.0"

  name                = "${data.naming_name.logic_app.name}-${each.key}"
  location            = var.location
  resource_group_name = var.resource_group_name
  resource_group_id   = data.azurerm_resource_group.this.id

  state = "Enabled" # decision: logic-app.workflows.state

  # decision: logic-app.workflows.trigger_authentication - Entra tokens, no SAS
  access_control = {
    triggers = {
      allowedCallerIpAddresses = []
      openAuthenticationPolicies = {
        policies = {
          callers = {
            type   = "AAD"
            claims = [{ name = "aud", value = "https://management.core.windows.net/" }]
          }
        }
      }
    }
  }

  managed_identities = { user_assigned_resource_ids = [var.identity_id] }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
      principal_type             = v.principal_type
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["WorkflowRuntime"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}
```

`logic_app_definition` is left at the module's empty definition: the workflow's triggers and
actions are content, deployed by the integration team's pipeline over this resource, and the
module's `ignore_changes` story for the definition is read from its README before the second
apply. The `access_control` map is in ARM spelling because the input is untyped.

### Tests

With `azapi` and `modtm` mocked, the site module's `resource` output is the `azapi_resource`, so
asserts target `module.logic_app.resource.body.properties.*` at plan time (`httpsOnly`,
`publicNetworkAccess`, `siteConfig.minTlsVersion`, `virtualNetworkSubnetId`) and `body.kind`
(`functionapp,workflowapp`); the plan module exposes only `name` and `resource_id`, so
`plan_sku`, `zone_redundant`, `instance_count` and `max_instance_count` are `# not-testable:`.
The workflow module's resource is `azurerm_logic_app_workflow`; what its `resource` output
exposes (`enabled`, `identity`) is read off a first `terraform test` on the pinned version, and
`access_control` is asserted where exposed, otherwise marked. App settings, the private endpoint,
role assignments and the diagnostic settings are children and `# not-testable:` with a reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource / argument |
|---|---|
| the plan | `azurerm_service_plan` (`os_type = "Windows"`, `sku_name = "WS1"`, `worker_count`, `maximum_elastic_worker_count`, `zone_balancing_enabled`) |
| the Standard app | `azurerm_logic_app_standard` (`app_service_plan_id`, `storage_account_name` with `storage_account_access_key` **or** `storage_key_vault_secret_id` + `key_vault_reference_identity_id`, `app_settings` for the identity triple, `https_only`, `public_network_access`, `virtual_network_subnet_id`, `ftp_publish_basic_authentication_enabled`, `scm_publish_basic_authentication_enabled`, `identity`, `site_config { min_tls_version, scm_min_tls_version, ftps_state, ip_restriction, ip_restriction_default_action, vnet_route_all_enabled, dotnet_framework_version }`) |
| the Consumption workflow | `azurerm_logic_app_workflow` (`enabled`, `identity`, `access_control { trigger { allowed_caller_ip_address_range, open_authentication_policy } }`, `workflow_parameters`) |
| private endpoint | `azurerm_private_endpoint` with `subresource_names = ["sites"]` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` and `enabled_metric { category }` |
