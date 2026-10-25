# Rendering a route table as Terraform

Mapping from the question set to the route table. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-routetable/azurerm` | **v0.5.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.5.0`. The git
tag list holds both `0.4.1` and `v0.5.0` - the unprefixed form is older; sort by version, not by
text.

**`azurerm` and AzAPI mixed**: the table is an `azurerm_route_table` (takes `resource_group_name`,
a name), its routes are AzAPI children. Requires `azurerm ~> 4.0`, `azapi ~> 2.4`, `modtm ~> 0.3`,
`random >= 3.5.0, < 4.0`, Terraform `>= 1.9` - a root calling it cannot be on `azurerm` 5.x or
`random` 4.x, and the authored fallback in that root follows the 4.x spelling. The root's provider
set is the union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| (the table) | `name` through the naming provider | `subname` carries the subnet role: `rt-gwc-dev-telemetry-spoke-01` |
| `default_route: firewall`, `firewall_private_ip` | `routes = { default = { name, address_prefix = "0.0.0.0/0", next_hop_type = "VirtualAppliance", next_hop_in_ip_address } }` | Written as an entry, so it shows in the plan |
| `routes` | further entries of `routes`, the key arbitrary and stable; `next_hop_type` one of `VirtualAppliance`, `VirtualNetworkGateway`, `VnetLocal`, `Internet`, `None` | `next_hop_in_ip_address` only for `VirtualAppliance` |
| `bgp_route_propagation` | `bgp_route_propagation_enabled` | `disabled` renders **`false`**; module default is `true`, the portal's too |
| `subnets` | not an input here | The association is the virtual-network set's `subnets.<k>.route_table = { id = module.route_table.resource_id }`; `subnet_resource_ids` stays empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.5.0: nothing from this question set. `routes_legacy_mode`,
`role_assignments` and `lock` are inputs the question set has no decision for - leave them
unset rather than inventing a default (`lock`: `deployment.resource_lock` does not list
network resources).

### The call

```hcl
data "naming_name" "route_table" {
  resource   = "Azure::Microsoft.Network/routeTables"
  parameters = { subname = "spoke" } # the subnet role
}

module "route_table" {
  source  = "Azure/avm-res-network-routetable/azurerm"
  version = "~> 0.5.0"

  name                = data.naming_name.route_table.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: route-table.networking.bgp_route_propagation - disabled renders false
  bgp_route_propagation_enabled = false

  routes = {
    # decision: route-table.networking.default_route
    default = {
      name                   = "default-to-firewall"
      address_prefix         = "0.0.0.0/0"
      next_hop_type          = "VirtualAppliance"
      next_hop_in_ip_address = var.firewall_private_ip # decision: route-table.networking.firewall_private_ip
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.route_table.resource_id }
```

Validated with `terraform validate` (registry, v0.5.0, `azurerm ~> 4.0`) in a root together with
the other four modules of this family.

### Tests

`mock_provider "azurerm"`, `"azapi"`, `"modtm"` and `"random"`; the naming provider stays real.
The `resource` output is the `azurerm_route_table`, so the name and the propagation flag are
observable; the routes are AzAPI children whose attributes are unknown at plan, so they are
counted and the rest is `# not-testable:`. Settled by a `terraform test` run on v0.5.0:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.route_table.resource.name == "rt-gwc-dev-telemetry-spoke-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

run "networking" {
  command = plan

  # decision: route-table.networking.bgp_route_propagation
  assert {
    condition     = module.route_table.resource.bgp_route_propagation_enabled == false
    error_message = "Disabled: a learned route must not pull spoke traffic past the firewall."
  }

  # decision: route-table.networking.default_route
  assert {
    condition     = length(module.route_table.routes) == 1
    error_message = "One entry for the default route to the firewall."
  }
}

# not-testable: route-table.networking.subnets - recorded in the spec; the association is rendered in the virtual-network set
# not-testable: route-table.networking.firewall_private_ip - the next hop is inside a module-internal azapi route; read from the plan JSON
# not-testable: route-table.networking.routes - as above
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource |
|---|---|
| the table, `bgp_route_propagation` | `azurerm_route_table` with `bgp_route_propagation_enabled` |
| `default_route`, `routes` | `azurerm_route` each (`address_prefix`, `next_hop_type`, `next_hop_in_ip_address`) **or** the table's inline `route` argument (a list of objects on 5.x, no longer a block) - **not both**, the two fight on every apply |
| `subnets` | `azurerm_subnet_route_table_association` - or the subnet's own `route_table_id`; one of them, never both |

Validated against `azurerm` 5.x.
