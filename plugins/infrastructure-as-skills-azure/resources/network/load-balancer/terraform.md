# Rendering a Load Balancer as Terraform

Mapping from the question set to the balancer. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

`Azure/avm-res-network-loadbalancer/azurerm` - the primary rendering. Documented against **v0.5.0**
(resolved 2026-10-25); resolve the current version and re-read its README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.5.0`. Status: Available.

**The module is `azurerm`-based with AzAPI beside it**: it takes `resource_group_name` (a name, not an
id) and requires `azurerm >= 4.0, < 5.0` - **a root calling it cannot be on 5.x** - `azapi ~> 2.4`,
`modtm ~> 0.3`, `random >= 3.5.0` and Terraform `>= 1.9, < 2.0`. The root's provider set is the union.

**The module creates the public IP** when a frontend sets `create_public_ip_address = true`, from
`public_ip_address_configuration`, and takes its name from `public_ip_address_resource_name`; a private
frontend takes a subnet id and the zones of the frontend. A rule, probe or NAT rule refers to a pool,
probe or frontend by its **map key / name** (`backend_address_pool_object_names`, `probe_object_name`,
`frontend_ip_configuration_name`), not by an id, so the keys in the call must match.

**The module's defaults are not the guardrails'.** A rule defaults to 3389 to 3389 and to
`enable_tcp_reset = false`, a probe to a 15-second interval, the private address to `Dynamic`, and
`disable_outbound_snat` to `false`: every one is written in the call.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku = "Standard"`, `sku_tier = "Regional"` | Module default; written |
| `zone_redundant` | `frontend_ip_configurations.<k>.zones = ["1", "2", "3"]` (or `["None"]` to omit them); the created public IP takes the same | A list of strings |
| `frontend_exposure` | private: `frontend_private_ip_subnet_resource_id`; public: `create_public_ip_address = true` | One frontend per entry |
| `frontend_subnet` | `frontend_ip_configurations.<k>.frontend_private_ip_subnet_resource_id` (or the module-wide `frontend_subnet_resource_id`) | |
| `private_ip_allocation`, `private_ip_address` | `frontend_private_ip_address_allocation = "Static"`, `frontend_private_ip_address` | Module default `Dynamic` |
| `public_ip_zone_redundant` | the same `zones` on the frontend; `public_ip_address_configuration = { allocation_method = "Static", sku = "Standard", sku_tier = "Regional" }` | Also `ddos_protection_mode = "VirtualNetworkInherited"`, the default |
| `backend_pools` | `backend_address_pools = { <k> = { name, virtual_network_resource_id } }`, `backend_address_pool_addresses` | A pool whose members are a scale set's joins from the scale set |
| `health_probe_protocol`, `health_probe_interval_seconds`, `health_probe_unhealthy_threshold` | `lb_probes.<k> = { name, protocol, port, interval_in_seconds, number_of_probes_before_removal, request_path }` | `request_path` only with `Http` / `Https`; the module validates the pair. `probe_threshold` (default 1) stays |
| `tcp_reset`, `load_distribution`, `floating_ip` | `lb_rules.<k>.enable_tcp_reset`, `.load_distribution`, `.enable_floating_ip` | Module defaults `false` / `Default` / `false` |
| `rules` | `lb_rules.<k> = { name, frontend_ip_configuration_name, protocol, frontend_port, backend_port, backend_address_pool_object_names, probe_object_name }` | Wiring: filled by the pattern; both ports always stated |
| `inbound_nat_rules` | `lb_nat_rules` | Empty |
| `outbound_snat`, `outbound_allocated_ports` | `lb_outbound_rules.<k> = { name, frontend_ip_configurations = [{ name }], backend_address_pool_object_name, number_of_allocated_outbound_ports }`; `lb_rules.<k>.disable_outbound_snat = true` | Only with the rule |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`, so it is set empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "naming_name" "load_balancer" {
  # `::internal` renders `lbi`, `::external` renders `lbe`.
  resource = "Azure::Microsoft.Network/loadBalancers::internal"
}

module "load_balancer" {
  source  = "Azure/avm-res-network-loadbalancer/azurerm"
  version = "~> 0.5.0"

  name                = data.naming_name.load_balancer.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: load-balancer.balancer.sku
  sku      = "Standard"
  sku_tier = "Regional"

  # decision: load-balancer.networking.frontend_exposure, frontend_subnet, private_ip_allocation, private_ip_address
  # decision: load-balancer.balancer.zone_redundant
  frontend_ip_configurations = {
    frontend = {
      name                                   = "frontend"
      frontend_private_ip_subnet_resource_id = var.frontend_subnet_id
      frontend_private_ip_address_allocation = "Static"
      frontend_private_ip_address            = var.private_ip_address
      zones                                  = ["1", "2", "3"]
    }
  }

  # decision: load-balancer.networking.backend_pools
  backend_address_pools = {
    for k, p in var.backend_pools : k => {
      name                        = p.name
      virtual_network_resource_id = p.virtual_network_id
    }
  }

  # decision: load-balancer.networking.health_probe_protocol, health_probe_interval_seconds, health_probe_unhealthy_threshold
  lb_probes = {
    for k, p in var.probes : k => {
      name                            = p.name
      protocol                        = "Tcp"
      port                            = p.port
      interval_in_seconds             = 5
      number_of_probes_before_removal = 2
    }
  }

  # decision: load-balancer.networking.rules, tcp_reset, load_distribution, floating_ip
  lb_rules = {
    for k, r in var.rules : k => {
      name                              = r.name
      frontend_ip_configuration_name    = "frontend"
      protocol                          = r.protocol
      frontend_port                     = r.frontend_port
      backend_port                      = r.backend_port
      backend_address_pool_object_names = [r.pool]
      probe_object_name                 = r.probe
      load_distribution                 = "Default"
      enable_floating_ip                = false
      enable_tcp_reset                  = true
    }
  }

  # decision: load-balancer.networking.inbound_nat_rules - none
  lb_nat_rules = {}

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = []
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.load_balancer.resource_id }
output "frontend_private_ip" { value = var.private_ip_address }
```

With `frontend_exposure: public` the frontend becomes
`{ name = "frontend", create_public_ip_address = true, public_ip_address_resource_name = data.naming_name.load_balancer_public_ip.name, zones = ["1", "2", "3"] }` and the module gets
`public_ip_address_configuration = { allocation_method = "Static", sku = "Standard", sku_tier = "Regional", ddos_protection_mode = "VirtualNetworkInherited" }`. With `outbound_snat: outbound_rule` every rule on that frontend gets
`disable_outbound_snat = true` and the module `lb_outbound_rules = { out = { name = "outbound", frontend_ip_configurations = [{ name = "frontend" }], backend_address_pool_object_name = "<pool key>", number_of_allocated_outbound_ports = 1024 } }`.

### Tests

`mock_provider "azurerm"`, `"azapi"` and `"modtm"` keep the plan credential-free. The module's `resource`
output is the `azurerm_lb` echoed from the inputs: `sku`, `sku_tier` and the frontend configuration
(`frontend_ip_configuration[0].zones`, `.private_ip_address_allocation`, `.subnet_id`) are asserted on
`module.load_balancer.resource`; the pools, probes and rules are child resources of the module and its
`azurerm_lb_probe` / `azurerm_lb_rule` outputs are read where they exist (exact paths from a first
`terraform test` on the pinned version). The diagnostic setting and the rules the pattern fills are
`# not-testable:` with that reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `sku`, `zone_redundant` | `azurerm_lb.sku = "Standard"`, `.sku_tier`; `frontend_ip_configuration { zones }` |
| `frontend_exposure` | `frontend_ip_configuration { subnet_id, private_ip_address_allocation, private_ip_address }` or `{ public_ip_address_id }`; `azurerm_public_ip` with `sku = "Standard"`, `allocation_method = "Static"`, `zones` |
| `backend_pools` | `azurerm_lb_backend_address_pool` (+ `_address`) |
| `health_probe_*` | `azurerm_lb_probe { protocol, port, request_path, interval_in_seconds, probe_threshold, number_of_probes }` |
| `rules`, `tcp_reset`, `load_distribution`, `floating_ip` | `azurerm_lb_rule { protocol, frontend_port, backend_port, frontend_ip_configuration_name, backend_address_pool_ids, probe_id, tcp_reset_enabled, load_distribution, floating_ip_enabled, disable_outbound_snat }` |
| `inbound_nat_rules` | `azurerm_lb_nat_rule` |
| `outbound_snat` | `azurerm_lb_outbound_rule { protocol, backend_address_pool_id, allocated_outbound_ports, frontend_ip_configuration { name } }` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_metric { category = "AllMetrics" }` |
