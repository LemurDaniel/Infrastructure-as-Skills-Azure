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

What each decision renders to - the input and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Decision | Input | Note |
|---|---|---|
| `role_assignments` | `role_assignments` | None here |
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

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.
