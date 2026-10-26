# Rendering an AI Foundry account as Terraform

Mapping from the question set to the account. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-cognitiveservices-account/azurerm` | **v0.11.1** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.11.0`.

**AzAPI-based, and still `azurerm`-constrained.** It takes `parent_id` (the resource group's
id) and requires `azapi ~> 2.5`, `modtm ~> 0.3`, `random`, `time ~> 0.10`, Terraform `>= 1.9`
- and `azurerm >= 4.17.0, < 5.0`, so **a root calling it cannot be on 5.x** although it
creates its resources through `azapi`.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `kind` | `kind` | `AIServices` or `OpenAI` |
| `sku_name` | `sku_name` | `S0` |
| (derived from the name) | `custom_subdomain_name` | **Required** for a firewall, private endpoints and token auth; default `null`; written |
| `project_management` | `allow_project_management` | Default `false`; written |
| `projects` | **not the module** - see below | The module takes project *names* (`associated_projects`, `default_project`) |
| `model_deployments`, `deployment_sku`, `deployment_capacity`, `version_upgrade_option`, `content_filter` | `cognitive_deployments = { <k> = { name, model = { format, name, version }, scale = { type, capacity }, version_upgrade_option, rai_policy_name } }` | `version_upgrade_option` module default `OnceNewDefaultVersionAvailable`; `scale.type` carries the deployment type |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default **`true`** |
| `ip_rules` | `network_acls = { default_action = "Deny", ip_rules }` | Needs `custom_subdomain_name`; read member names from the README |
| `restrict_outbound` | `outbound_network_access_restricted` | Default `null` (off); written |
| `allowed_fqdns` | `fqdns` | Only with `restrict_outbound`; the host names, no wildcards |
| `private_endpoint_subnet` | `private_endpoints = { account = { subnet_resource_id } }` | |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `role_assignments` | `role_assignments` | |
| `local_authentication_disabled` | `local_auth_enabled` | **Inverse**; default `null` (on); written |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | Unversioned |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories, or every log is collected beside them |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "foundry" {
  source  = "Azure/avm-res-cognitiveservices-account/azurerm"
  version = "~> 0.11.0"

  name      = data.naming_name.foundry.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  kind     = "AIServices"
  sku_name = "S0"
  # the hostname - required for the firewall, private endpoints and token auth
  custom_subdomain_name = data.naming_name.foundry.name

  allow_project_management = true

  # decision: foundry.models.* - one entry per deployment; the model and version are pinned
  cognitive_deployments = {
    chat = {
      name = "chat"
      model = {
        format  = "OpenAI"
        name    = "gpt-4.1"
        version = "2025-04-14"
      }
      scale = {
        type     = "DataZoneStandard"
        capacity = 10
      }
      version_upgrade_option = "OnceCurrentVersionExpired"
      rai_policy_name        = "Microsoft.DefaultV2"
    }
  }

  # decision: foundry.networking.public_network_access - a bool, module default true
  public_network_access_enabled      = false
  outbound_network_access_restricted = true
  private_endpoints = {
    account = {
      name               = data.naming_name.foundry_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: foundry.identity.managed_identity - none; `{ system_assigned = true }` once it reaches storage or search
  managed_identities = {}

  # decision: foundry.security.local_authentication_disabled - inverse input
  local_auth_enabled = false

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.foundry.resource_id }
```

The model name and version above are an example of the shape; the real ones are looked up
against the region's catalogue (`az cognitiveservices model list --location <region>`).

### Another region

When the spec carries `resources.<key>.placement.location`, the account takes its own
variable, one value in every stage file. The private endpoint names the network's region: the
module falls back to the **account's** `location`, and an endpoint outside its subnet's region
fails at apply. The names do not change - the account's pattern carries no region, and the
endpoint's region is `var.location`.

```hcl
# decision: foundry.placement.location - departs from var.location for the model catalogue
variable "foundry_location" {
  type        = string
  description = "Region of the Foundry account, apart from var.location."
}

module "foundry" {
  # ...
  location = var.foundry_location
  private_endpoints = {
    account = {
      name               = data.naming_name.foundry_private_endpoint.name
      location           = var.location # the subnet's region, never the account's
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
}
```

The projects take `var.foundry_location` too. The test asserts the account on
`var.foundry_location` and the endpoint on `var.location`.

### Projects

Neither this module nor the Bicep one creates a project. They are rendered next to it as
child resources, each with its own system-assigned identity:

```hcl
resource "azapi_resource" "project" {
  for_each = toset(var.projects)

  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name      = each.key
  parent_id = module.foundry.resource_id
  location  = var.location

  body = {
    identity   = { type = "SystemAssigned" }
    properties = {}
  }
  depends_on = [module.foundry]
}
```

`2025-06-01` is a GA version of the type (listed by `az provider show -n Microsoft.CognitiveServices`
on 2026-10-25; newer GA versions exist). Look the current one up the same way, and check the
pinned `azapi` knows it before moving up: an unknown version fails schema validation.

### Tests

With `azapi` and `modtm` mocked, the module's `resource` output is the account's `azapi`
resource, so asserts target its body at plan time (`properties.publicNetworkAccess`,
`properties.disableLocalAuth`, `properties.customSubDomainName`, `properties.restrictOutboundNetworkAccess`,
`properties.allowProjectManagement`) - the exact paths read off a first `terraform test` run.
Deployments are child resources and are `# not-testable:` where the plan hides them.

## Authored rendering

The fallback. Targets `azurerm` **5.x** (`azurerm_cognitive_account`, `azurerm_cognitive_account_project`,
`azurerm_cognitive_deployment`); check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `kind`, `sku_name`, `custom_subdomain_name` | `azurerm_cognitive_account` `kind`, `sku_name`, `custom_subdomain_name` |
| `project_management` | `project_management_enabled` (in 5.x; it was not in 4.x, where the account needed `azapi_resource`) |
| `public_network_access`, `ip_rules` | `public_network_access_enabled`, `network_acls` |
| `restrict_outbound` | `outbound_network_access_restricted` |
| `allowed_fqdns` | `fqdns` |
| `local_authentication_disabled` | `local_auth_enabled` (inverse) |
| `projects` | `azurerm_cognitive_account_project` (`cognitive_account_id`, `location`, `identity`) - the resource the AVM module lacks |
| deployments | `azurerm_cognitive_deployment` (`model`, `sku`) |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
