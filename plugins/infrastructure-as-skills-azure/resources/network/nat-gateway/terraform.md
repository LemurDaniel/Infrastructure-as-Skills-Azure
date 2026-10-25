# Rendering a NAT gateway as Terraform

Mapping from the question set to the NAT gateway. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-natgateway/azurerm` | **v0.3.2** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.2`.

**AzAPI only**: it takes `parent_id` (the resource group's id) and requires `azapi ~> 2.4`,
`modtm ~> 0.3`, `random ~> 3.6`, Terraform `~> 1.9`; no `azurerm`. The root's provider set is the
union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku_name` | **Module default is `StandardV2`**, the Bicep module's `Standard`: written on every call |
| `zone` | `zones = ["1"]` for `Standard`; `null` for `none` | Ignored by the module for `StandardV2`, which is always `["1", "2", "3"]` |
| `public_ip_source: with_gateway`, `public_ip_count` | `public_ips = { ip_1 = { name }, ... }` and `public_ip_configuration` with the **same keys** | 1 to 16 entries; the names come from the naming provider's `at_index`. Keys must match between the two inputs |
| the addresses' SKU, allocation, zones | `public_ip_configuration.<k> = { sku, allocation_method = "Static", zones }` | `sku` equal to `sku_name`; module default `StandardV2` for both. `zones` are **strings** here, unlike the public IP module's numbers |
| `public_ip_source: separate` | `public_ip_resource_ids` | The ids from the `public-ip-address` set (`purpose: nat_gateway`) |
| `public_ip_prefix_ids` | `public_ip_prefix_resource_ids` | IPv4 only |
| `idle_timeout_minutes` | `idle_timeout_in_minutes` | The gateway's; the addresses' own `idle_timeout_in_minutes` (default 30) is not used for NAT traffic |
| `subnets` | not an input here | The association is the virtual-network set's `subnets.<k>.nat_gateway = { id = module.nat_gateway.resource_id }` |
| `diagnostic_workspace`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, metrics = [{ category = "AllMetrics" }] } }` | The object form (`logs`, `metrics`), not the category-set form; no logs for a NAT gateway |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.3.2: nothing from this question set. `public_ip_v6_resource_ids`,
`public_ip_prefix_v6_resource_ids`, `role_assignments` and `lock` are inputs the question set
has no decision for - leave them unset rather than inventing a default.

### The call

```hcl
data "naming_name" "nat_gateway" {
  resource = "Azure::Microsoft.Network/natGateways"
}

# One name per address through the convention's `name` parameter: the pattern for public IPs has
# no SUBNAME token. at_index holds `count` names in order.
data "naming_name" "nat_public_ip" {
  resource   = "Azure::Microsoft.Network/publicIPAddresses"
  parameters = { name = "${var.workload}-nat" }
  index      = { start = 0, count = 1 } # nat-gateway.gateway.public_ip_count
}

module "nat_gateway" {
  source  = "Azure/avm-res-network-natgateway/azurerm"
  version = "~> 0.3.2"

  name      = data.naming_name.nat_gateway.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: nat-gateway.gateway.sku
  sku_name = "StandardV2"
  # decision: nat-gateway.gateway.idle_timeout_minutes
  idle_timeout_in_minutes = 4

  # decision: nat-gateway.gateway.public_ip_source - with_gateway; one entry per address
  # decision: nat-gateway.gateway.public_ip_count
  public_ips = {
    for i, n in data.naming_name.nat_public_ip.at_index : "ip_${i + 1}" => { name = n }
  }
  public_ip_configuration = {
    for i, n in data.naming_name.nat_public_ip.at_index : "ip_${i + 1}" => {
      sku               = "StandardV2" # must match sku_name
      allocation_method = "Static"
      zones             = ["1", "2", "3"]
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      # decision: nat-gateway.observability.metrics_enabled - a NAT gateway has no log categories
      metrics = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.nat_gateway.resource_id }
```

For `sku: Standard` the call is `sku_name = "Standard"`, `zones = ["1"]` (or omitted for `none`)
and `sku = "Standard"` in `public_ip_configuration`. Validated with `terraform validate`
(registry, v0.3.2) in a root together with the other four modules of this family, and the
`StandardV2` form with a plan.

### Tests

`mock_provider "azapi"`, `"modtm"`, `"random"` and `"azurerm"` (for the data source of the
resource group); the naming provider stays real. The `resource` output is the gateway's
`azapi_resource`, and `public_ip_resource` the addresses', so the body is observable at plan. Settled
by a `terraform test` run on v0.3.2:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = data.naming_name.nat_gateway.name == "ng-gwc-dev-telemetry-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

run "gateway" {
  command = plan

  # decision: nat-gateway.gateway.sku
  assert {
    condition     = module.nat_gateway.resource.body.sku.name == "StandardV2"
    error_message = "StandardV2: zone-redundant by design; the module default must not decide it."
  }

  # decision: nat-gateway.gateway.idle_timeout_minutes
  assert {
    condition     = module.nat_gateway.resource.body.properties.idleTimeoutInMinutes == 4
    error_message = "The gateway's timeout, not the address default of 30."
  }

  # decision: nat-gateway.gateway.public_ip_source
  assert {
    condition     = module.nat_gateway.public_ip_resource["ip_1"].body.sku.name == "StandardV2" && module.nat_gateway.public_ip_resource["ip_1"].body.properties.publicIPAllocationMethod == "Static"
    error_message = "Addresses created with the gateway match its SKU and are static."
  }

  # decision: nat-gateway.gateway.public_ip_count
  assert {
    condition     = length(module.nat_gateway.public_ip_resource) == 1 && length(module.nat_gateway.resource.body.properties.publicIpAddresses) == 1
    error_message = "One address, as many entries as the count says."
  }

  # decision: nat-gateway.gateway.public_ip_prefix_ids
  assert {
    condition     = length(module.nat_gateway.resource.body.properties.publicIpPrefixes) == 0
    error_message = "No prefix unless the customer named one."
  }
}

# not-testable: nat-gateway.gateway.subnets - recorded in the spec; the association is rendered in the virtual-network set
# not-testable: nat-gateway.gateway.zone - not reached for StandardV2; for Standard assert body.zones
# not-testable: nat-gateway.observability.diagnostic_workspace - the diagnostic setting is a module-internal azapi resource
# not-testable: nat-gateway.observability.metrics_enabled - as above
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource |
|---|---|
| the gateway, `sku`, `zone`, `idle_timeout_minutes` | `azurerm_nat_gateway` (`sku_name`, `zones`, `idle_timeout_in_minutes`) |
| the addresses | `azurerm_public_ip` (see the `public-ip-address` set) + `azurerm_nat_gateway_public_ip_association`; a prefix with `azurerm_nat_gateway_public_ip_prefix_association` |
| `subnets` | `azurerm_subnet_nat_gateway_association` - the subnet has no argument for it, so this is the one form |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_metric { category }` |

Validated against `azurerm` 5.x (gateway and associations).
