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

What each decision renders to - the input and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Input | Note |
|---|---|---|
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

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.
