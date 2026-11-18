# Rendering an Azure Bot as Terraform

Mapping from the question set to the bot. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-botservice-botservice/azurerm` | **v0.6.0** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.6.0`; the module is
young (first published 2026-01) and its inputs move.

**AzAPI only**: it takes `resource_group_name` (a name), requires `azapi ~> 2.12`, `modtm ~> 0.3`,
`random ~> 3.7` and Terraform `~> 1.5`, and no `azurerm` - a root may be on `azurerm` 5.x. The
channels, private endpoints, role assignments and diagnostic settings are `azapi_resource`s of the
module.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| (kind) | `kind = "azurebot"` | Module default; written |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not used: `developer_app_insights_*` (take an API key - the application carries its own
connection string), `luis_*` (retired), `storage_resource_id`.

### The call

```hcl
module "bot" {
  source  = "Azure/avm-res-botservice-botservice/azurerm"
  version = "~> 0.6.0"

  name                = data.naming_name.bot.name
  location            = "global"
  resource_group_name = var.resource_group_name

  kind         = "azurebot"
  sku          = "S1" # decision: bot-service.bot.sku - the module default is F0
  display_name = var.bot_display_name
  endpoint     = var.messaging_endpoint # decision: bot-service.bot.messaging_endpoint

  # decision: bot-service.bot.app_identity_type, bot_identity - the module default is MultiTenant
  microsoft_app_type      = "UserAssignedMSI"
  microsoft_app_id        = var.bot_identity_client_id
  microsoft_app_msi_id    = var.bot_identity_id
  microsoft_app_tenant_id = var.tenant_id

  # decision: bot-service.bot.channels - names only; the channel settings are content
  channels = {
    directline = { channel_name = "DirectLineChannel", location = "global" }
  }
  streaming_endpoint_enabled = false # decision: bot-service.bot.streaming_endpoint

  # decision: bot-service.networking.public_network_access - the string form, not the bool
  public_network_access = "Disabled"
  # decision: bot-service.networking.private_endpoint_subnet, private_endpoint_subresources
  private_endpoints = {
    bot = {
      name               = data.naming_name.bot_private_endpoint_bot.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "Bot"
    }
    token = {
      name               = data.naming_name.bot_private_endpoint_token.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "Token"
    }
  }
  # private_dns_records: policy - the platform policy writes the records
  private_endpoints_manage_dns_zone_group = false

  # decision: bot-service.security.local_authentication_disabled - inverse input
  local_authentication_enabled = false
  # decision: bot-service.security.key_management
  is_cmek_enabled = false

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
      log_categories        = ["BotRequest"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.bot.resource_id }
```

`var.bot_identity_client_id` and `var.bot_identity_id` come from the identity set's outputs; the
same identity is assigned to the bot application by its set. With `key_management:
customer_managed` the call carries `is_cmek_enabled = true` and `cmek_key_vault_url = var.cmk_key_url`.

### Tests

With `azapi` and `modtm` mocked, the module's `resource` output is the bot's `azapi_resource`, so
asserts target `module.bot.resource.body.properties.*` (`msaAppType`, `msaAppId`, `endpoint`,
`publicNetworkAccess`, `disableLocalAuth`, `isStreamingSupported`, `isCmekEnabled`) and
`body.sku.name`, `body.kind` - the exact paths read off a first `terraform test` on the pinned
version. Channels, private endpoints, role assignments and the diagnostic setting are children
and `# not-testable:` with a reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x** (`azurerm_bot_service_azure_bot`); check against
`terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
