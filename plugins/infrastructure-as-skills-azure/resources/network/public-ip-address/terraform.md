# Rendering a public IP address as Terraform

Mapping from the question set to the public IP address. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-publicipaddress/azurerm` | **v0.2.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.1`.

**`azurerm`-based**: it takes `resource_group_name` (a name, not an id) and requires
`azurerm >= 3.116, < 5.0`, `azapi ~> 2.4`, `modtm ~> 0.3`, `random >= 3.5.0`, Terraform
`>= 1.0` - a root calling it cannot be on `azurerm` 5.x, and the authored fallback in that root
follows the 4.x spelling. The root's provider set is the union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.2.1: nothing from this question set. `ip_tags`,
`public_ip_prefix_id`, `reverse_fqdn` and `edge_zone` are inputs the question set has no
decision for - leave them unset rather than inventing a default.

### The call

```hcl
data "naming_name" "public_ip" {
  resource   = "Azure::Microsoft.Network/publicIPAddresses"
  parameters = { name = "${var.workload}-natgw" } # the pattern for public IPs has no SUBNAME token
}

module "public_ip" {
  source  = "Azure/avm-res-network-publicipaddress/azurerm"
  version = "~> 0.2.1"

  name                = data.naming_name.public_ip.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: public-ip-address.address.sku
  sku = "Standard"
  # decision: public-ip-address.address.sku_tier
  sku_tier = "Regional"
  # decision: public-ip-address.address.allocation_method
  allocation_method = "Static"
  # decision: public-ip-address.address.ip_version
  ip_version = "IPv4"
  # decision: public-ip-address.address.zones - a set of numbers, not strings
  zones = [1, 2, 3]
  # decision: public-ip-address.address.idle_timeout_minutes
  idle_timeout_in_minutes = 4
  # decision: public-ip-address.address.dns_label - null is no label; the module takes no empty string
  domain_name_label = null

  # decision: public-ip-address.security.ddos_protection_mode
  ddos_protection_mode = "VirtualNetworkInherited"
  # ddos_protection_plan_id = <the plan's id> - only with ddos_protection_mode = "Enabled"

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      # decision: public-ip-address.observability.diagnostic_categories
      log_categories = ["DDoSProtectionNotifications", "DDoSMitigationFlowLogs", "DDoSMitigationReports"]
      log_groups     = []
      # decision: public-ip-address.observability.metrics_enabled
      metric_categories = ["AllMetrics"]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.public_ip.resource_id }
output "ip_address" { value = module.public_ip.public_ip_address }
```

Validated with `terraform validate` (registry, v0.2.1, `azurerm ~> 4.0`) in a root together
with the other four modules of this family - the provider union resolves. The consumer takes
`module.public_ip.resource_id`; the address itself (`public_ip_address`) is the value the
handover lists for a partner's allowlist.

### Tests

`mock_provider "azurerm"`, `"azapi"`, `"modtm"` and `"random"`; the naming provider stays real.
The module exposes **no `resource` output** - its outputs are `name`, `public_ip_address`,
`public_ip_id` and `resource_id`, the last three unknown at plan - so the name is the one thing
a plan shows, and the decisions are marked `# not-testable:` with that reason. Settled by a
`terraform test` run on v0.2.1:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.public_ip.name == "pip-gwc-dev-telemetry-natgw-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

# not-testable: public-ip-address.address.purpose - it is the name's workload part, asserted above
# not-testable: public-ip-address.address.sku - the module has no resource output; azurerm_public_ip is inside it
# not-testable: public-ip-address.address.sku_tier - as above
# not-testable: public-ip-address.address.allocation_method - as above
# not-testable: public-ip-address.address.ip_version - as above
# not-testable: public-ip-address.address.zones - as above
# not-testable: public-ip-address.address.idle_timeout_minutes - as above
# not-testable: public-ip-address.address.dns_label - as above
# not-testable: public-ip-address.security.ddos_protection_mode - as above
# not-testable: public-ip-address.security.ddos_protection_plan - as above
# not-testable: public-ip-address.observability.diagnostic_workspace - the diagnostic setting is inside the module
# not-testable: public-ip-address.observability.diagnostic_categories - as above
# not-testable: public-ip-address.observability.metrics_enabled - as above
```

Where an assert on the SKU or the zones matters (a render that must never produce `Basic`),
render the address authored, below: `azurerm_public_ip.this.sku` is then an attribute of the
root.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Argument |
|---|---|
| the address | `azurerm_public_ip` |

Validated against `azurerm` 5.x.
