# Rendering Front Door as Terraform

Mapping from the question set to the profile. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

Front Door Standard and Premium are resources of the **CDN profile** (`Microsoft.Cdn/profiles`);
the AVM module is the CDN profile module and carries both products. Only the `front_door_*`
inputs are used here.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-cdn-profile/azurerm` | **v0.1.9** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.9`; the module is
pre-1.0, so expect inputs to move.

**AzAPI-based with an `azurerm` constraint**: it takes `resource_group_name` (a name) and requires
`azapi ~> 2.4`, `azurerm ~> 4.0` - **a root calling it cannot be on 5.x** - plus `modtm ~> 0.3`,
`random >= 3.5.0` and Terraform `>= 1.9`. The root's provider set is the union with the other
modules. The firewall policy is part of this module (`front_door_firewall_policies`,
`front_door_security_policies`), unlike in Bicep.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku` | `Standard_AzureFrontDoor` (module default) / `Premium_AzureFrontDoor`; written |
| `response_timeout_seconds` | `response_timeout_seconds` | **Module default 120** (Bicep 60); written |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `origins`, `origin_connection` | `front_door_origin_groups`, `front_door_origins` | A private-link origin sets the `private_link` member; the connection is created *pending* |
| `forwarding_protocol`, `https_redirect`, `caching` | `front_door_routes.<k> = { forwarding_protocol, https_redirect_enabled, cache }` | Route default for the protocol is `MatchRequest`; written |
| `custom_domains`, `certificate_source`, `minimum_tls_version` | `front_door_custom_domains.<k> = { host_name, tls = { certificate_type, minimum_tls_version } }` | `ManagedCertificate` / `CustomerCertificate`; `TLS12` |
| `waf_enabled`, `waf_mode`, `waf_managed_rules`, `waf_rate_limit_per_minute` | `front_door_firewall_policies = { <k> = { name, resource_group_name, sku_name, mode, custom_rules, managed_rules } }`, `front_door_security_policies` | `resource_group_name`, `sku_name` and `mode` are **required** members; the policy's `sku_name` must match the profile's; managed rule sets need Premium; the rate limit is a custom rule of type `RateLimitRule`; the security policy binds the policy to the endpoint and domains |
| `role_assignments` | `role_assignments` | None here |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "front_door" {
  source  = "Azure/avm-res-cdn-profile/azurerm"
  version = "~> 0.1.9"

  name                = data.naming_name.front_door.name
  location            = "global"
  resource_group_name = var.resource_group_name

  # decision: front-door.profile.sku - the module default is Standard
  sku = "Premium_AzureFrontDoor"
  # decision: front-door.profile.response_timeout_seconds - the module default is 120
  response_timeout_seconds = 60

  front_door_endpoints      = var.front_door_endpoints
  front_door_origin_groups  = var.front_door_origin_groups
  front_door_origins        = var.front_door_origins
  front_door_routes         = var.front_door_routes
  front_door_custom_domains = var.front_door_custom_domains

  # decision: front-door.security.* - the firewall policy and the security policy that binds it
  front_door_firewall_policies = {
    waf = {
      name                = data.naming_name.front_door_waf.name
      resource_group_name = var.resource_group_name
      sku_name            = "Premium_AzureFrontDoor"
      mode                = "Prevention"
      # a custom rule with action Block needs a response status code
      custom_block_response_status_code = 403
      # decision: front-door.security.waf_rate_limit_per_minute
      custom_rules = {
        rate = {
          name                           = "RateLimit"
          priority                       = 1
          type                           = "RateLimitRule"
          action                         = "Block"
          rate_limit_duration_in_minutes = 1
          rate_limit_threshold           = 1000
          match_conditions = {
            all = {
              match_variable = "RequestUri"
              operator       = "Contains"
              match_values   = ["/"]
            }
          }
        }
      }
      # decision: front-door.security.waf_managed_rules - Premium only
      managed_rules = {
        default = { type = "Microsoft_DefaultRuleSet", version = "2.1", action = "Block" }
        bots    = { type = "Microsoft_BotManagerRuleSet", version = "1.1", action = "Block" }
      }
    }
  }
  front_door_security_policies = var.front_door_security_policies

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["FrontDoorAccessLog", "FrontDoorHealthProbeLog", "FrontDoorWebApplicationFirewallLog"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.front_door.resource_id }
```

The module requires a `location` argument; a Front Door profile is `global`, so that is the value, whatever `context.location` says. A Private Link origin
raises a connection on the **origin's** resource: the render outputs its name and the handover
says who approves it. Until then the origin is unreachable and the health probe fails.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the profile
is an `azapi_resource`, so asserts target its `body.sku.name`, `body.properties.originResponseTimeoutSeconds`,
and the firewall policy's `body.properties.policySettings`. Routes, origins, domains and the
security policy are marked `# not-testable:` with a reason where the plan does not show them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `sku`, `response_timeout_seconds` | `azurerm_cdn_frontdoor_profile.sku_name`, `.response_timeout_seconds` |
| `origins` | `azurerm_cdn_frontdoor_origin_group`, `azurerm_cdn_frontdoor_origin` (`private_link { ... }`) |
| `forwarding_protocol`, `https_redirect`, `caching` | `azurerm_cdn_frontdoor_route` |
| `custom_domains` | `azurerm_cdn_frontdoor_custom_domain { tls { certificate_type, minimum_tls_version } }` |
| WAF | `azurerm_cdn_frontdoor_firewall_policy`, `azurerm_cdn_frontdoor_security_policy` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
