# Rendering an Application Gateway as Terraform

Mapping from the question set to the gateway. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-applicationgateway/azurerm` | **v0.5.3** | 2026-10-25 | Available |
| `Azure/avm-res-network-applicationgatewaywebapplicationfirewallpolicy/azurerm` | **v0.2.0** | 2026-10-25 | Available |
| `Azure/avm-res-network-publicipaddress/azurerm` | **v0.2.1** | 2026-10-25 | Available |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pins are `~> 0.5.3` and `~> 0.2.0`.

**The gateway module is AzAPI-based with a wide `azurerm` range**: it takes `parent_id` (the resource
group's id, not its name) and requires `azapi ~> 2.9`, `azurerm >= 3.117, < 5.0` - **a root calling it cannot be on 5.x** -
`modtm ~> 0.3`, `random ~> 3.5` and **Terraform `>= 1.12`**. The WAF policy module is
`azurerm`-based (`~> 4.2`), no `azapi`, and takes `resource_group_name`. **The gateway module creates no
public IP** (an input that did so exists on the module's main branch but not in v0.5.3): the address
is the public IP module's, referenced by id. The root's provider set is the union.

The firewall is a **separate module and a separate resource**: the gateway references the
policy by id (`firewall_policy = { id }`). The legacy inline `web_application_firewall_configuration`
is not used - it cannot hold the managed rule set versions.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `waf_enabled` | `sku = { name = "WAF_v2", tier = "WAF_v2" }` and `firewall_policy = { id }` | `Standard_v2` when off; module default `null` (unset) - written |
| `waf_mode` | policy module `policy_settings = { mode, enabled }` | `Prevention` / `Detection`; written |
| `waf_rule_set`, `waf_bot_protection` | policy module `managed_rules = { managed_rule_set = [...] }` | Type and version of each set; read the member names from the README |
| `waf_exclusions` | policy module `managed_rules.exclusion` | |
| `capacity_min`, `capacity_max` | `autoscale_configuration = { min_capacity, max_capacity }` | `sku.capacity` stays unset when autoscale is set |
| `zone_redundant` | `zones = ["1", "2", "3"]` (a list) or `null` | Also on the public IP |
| `gateway_subnet` | `gateway_ip_configurations = [{ name, properties = { subnet = { id } } }]` | A list of objects |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { user_assigned_resource_ids }` | |
| `frontend_exposure` | `frontend_ip_configurations = [{ name, properties = { public_ip_address = { id }, subnet = { id }, private_ip_address, private_ip_allocation_method } }]` | A public gateway: the public IP module's `resource_id` in `public_ip_address.id`. A private-only gateway needs the subscription enrolled in the private application gateway feature |
| `public_ip_zone_redundant` | public IP module `zones` | `["1", "2", "3"]`; `allocation_method = "Static"`, `sku = "Standard"` |
| `tls_policy` | `ssl_policy = { policy_type = "Predefined", policy_name }` | Module default `null`. `min_protocol_version` is for a custom policy |
| `backend_protocol` | `backend_http_settings_collection.<k>.protocol` | `Https` / `Http`; port 443 / 80 |
| `redirect_http_to_https` | `redirect_configurations` + a `request_routing_rules` entry on the port-80 listener | |
| `http2_enabled` | `enable_http2` | Module default `null`; written |
| `listeners` | `http_listeners`, `backend_address_pools`, `probes`, `request_routing_rules`, `ssl_certificates` | Wiring: filled by the pattern. A certificate is `{ name, key_vault_secret_id }` |
| `role_assignments` | `role_assignments` | None here; the gateway has no data plane |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "waf_policy" {
  source  = "Azure/avm-res-network-applicationgatewaywebapplicationfirewallpolicy/azurerm"
  version = "~> 0.2.0"

  name                = data.naming_name.waf_policy.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: application-gateway.gateway.waf_mode
  policy_settings = {
    enabled = true
    mode    = "Prevention"
  }
  # decision: application-gateway.gateway.waf_rule_set, waf_bot_protection
  managed_rules = var.waf_managed_rules

  enable_telemetry = true
  tags             = local.tags
}

module "public_ip" {
  source  = "Azure/avm-res-network-publicipaddress/azurerm"
  version = "~> 0.2.1"

  name                = data.naming_name.application_gateway_public_ip.name
  location            = var.location
  resource_group_name = var.resource_group_name

  allocation_method = "Static"
  sku               = "Standard"
  # decision: application-gateway.networking.public_ip_zone_redundant
  zones = ["1", "2", "3"]

  enable_telemetry = true
  tags             = local.tags
}

module "application_gateway" {
  source  = "Azure/avm-res-network-applicationgateway/azurerm"
  version = "~> 0.5.3"

  name      = data.naming_name.application_gateway.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: application-gateway.gateway.waf_enabled
  sku = {
    name = "WAF_v2"
    tier = "WAF_v2"
  }
  firewall_policy = { id = module.waf_policy.resource_id }
  # decision: application-gateway.gateway.capacity_min, capacity_max
  autoscale_configuration = {
    min_capacity = 2
    max_capacity = 10
  }
  # decision: application-gateway.gateway.zone_redundant
  zones = ["1", "2", "3"]

  gateway_ip_configurations = [{
    name = "gateway-ip"
    properties = {
      subnet = { id = var.gateway_subnet_id }
    }
  }]
  # decision: application-gateway.networking.frontend_exposure
  frontend_ip_configurations = [{
    name = "public"
    properties = {
      public_ip_address = { id = module.public_ip.resource_id }
    }
  }]

  managed_identities = {
    user_assigned_resource_ids = var.user_assigned_identity_ids
  }

  # decision: application-gateway.networking.tls_policy, http2_enabled
  ssl_policy = {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101S"
  }
  enable_http2 = true

  # ports, listeners, pools, probes, rules and certificates: the pattern's wiring
  frontend_ports                   = var.frontend_ports
  http_listeners                   = var.http_listeners
  backend_address_pools            = var.backend_address_pools
  backend_http_settings_collection = var.backend_http_settings
  probes                           = var.probes
  request_routing_rules            = var.request_routing_rules
  ssl_certificates                 = var.ssl_certificates

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["ApplicationGatewayAccessLog", "ApplicationGatewayFirewallLog"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.application_gateway.resource_id }
```

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the gateway
is an `azapi_resource`, so asserts target its `body.sku`, `body.properties.autoscaleConfiguration`,
`sslPolicy`, `enableHttp2` and `zones`, and the policy's `policy_settings` on its own resource -
exact paths are read off a first `terraform test` on the pinned versions. The diagnostic setting,
the public IP and the listener wiring are marked `# not-testable:` with a reason where the plan
does not show them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `waf_enabled`, `capacity_*` | `azurerm_application_gateway.sku { name, tier }`, `.autoscale_configuration { min_capacity, max_capacity }` |
| `zone_redundant` | `.zones` |
| `waf_mode`, rule sets | `azurerm_web_application_firewall_policy` with `policy_settings`, `managed_rules`; `.firewall_policy_id` on the gateway |
| `tls_policy` | `.ssl_policy { policy_type, policy_name }` |
| `http2_enabled` | `.http2_enabled` (the AVM module input is `enable_http2`) |
| `managed_identity` | `.identity { type, identity_ids }` |
| `gateway_subnet` | `.gateway_ip_configuration { subnet_id }` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
