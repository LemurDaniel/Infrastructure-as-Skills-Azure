# Rendering a virtual network as Terraform

Mapping from the question set to `azurerm_virtual_network` and `azurerm_subnet`. General
layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

`Azure/avm-res-network-virtualnetwork/azurerm` — the primary rendering for
`network_ownership: create`. Documented against **v0.22.3** (resolved 2026-10-17); resolve
the current version and re-read its README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. AzAPI-based: `azapi ~> 2.12`,
`modtm`, `random`, and the resource group as `parent_id`.

A referenced network (`network_ownership: reference`) stays a `data` block as below — the
module has a `subnet` child module for adding a subnet to a vnet it does not own, which is
the one case a referenced hub needs it, and that is a platform-team change, not this
deployment's.

### Decision → module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| diagnostics (from the deployment set) | `diagnostic_settings = { <key> = { workspace_resource_id, log_groups = [], metric_categories = ["AllMetrics"] } }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

The module also takes `peerings` — the spoke-to-hub peering a `landing_zone: corp` network
needs is an input here rather than a separate resource, and a pattern skill supplies it.

### The call

```hcl
module "network" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "~> 0.22.0"

  name      = data.naming_name.virtual_network.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: virtual-network.addressing.address_space
  address_space = [var.address_space]

  subnets = {
    for name, s in var.subnets : name => {
      name             = name
      address_prefixes = [s.prefix]
      # Enabled, so the subnet's NSG and routes apply to private endpoint traffic.
      private_endpoint_network_policies = "Enabled"
      service_endpoints                 = lookup(s, "service_endpoints", [])
      # Set by the NSG, route table and NAT gateway sets that reference this subnet (the
      # digest's `-- on parts`): subnet name -> id maps from the root, null where none claims it.
      network_security_group = try({ id = var.network_security_group_ids[name] }, null)
      route_table            = try({ id = var.route_table_ids[name] }, null)
      nat_gateway            = try({ id = var.nat_gateway_ids[name] }, null)
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.network.resource_id }

# Keyed by subnet name, so a consumer writes module.network.subnets["endpoints"].
output "subnet_ids" {
  value = { for k, s in module.network.subnets : k => s.resource_id }
}
```

### Tests

`azapi` and `modtm` mocked; the address space asserted through `module.network.resource.body`,
the subnets through `module.network.subnets` where the plan knows them, the rest marked as
[avm.md](../../../core/iac-rendering/references/avm.md#tests-with-a-module-in-the-middle)
describes.

## Authored rendering

The fallback — `implementation: authored`, a repository that already renders the network
this way, or reading what the module does inside.

## Decision → argument

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

## The network and its subnets

```hcl
resource "azurerm_virtual_network" "this" {
  name                = data.naming_name.virtual_network.name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.address_space]

  tags = local.tags
}

resource "azurerm_subnet" "this" {
  for_each = var.subnets

  name                 = each.key
  resource_group_name  = azurerm_virtual_network.this.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [each.value.prefix]

  # Enabled, so the subnet's NSG and routes apply to private endpoint traffic.
  private_endpoint_network_policies = "Enabled"

  service_endpoints = lookup(each.value, "service_endpoints", [])
}
```

`for_each` over a map keyed by subnet name, never `count`. With `count`, removing the
second of three subnets renumbers the third and Terraform plans a destroy and recreate of
a subnet that did not change — and a subnet recreate takes its private endpoints with it.

Never set a `subnet` block on `azurerm_virtual_network` while also declaring
`azurerm_subnet` resources. Both own the same API field, so each apply undoes the other.

## Delegation

```hcl
  dynamic "delegation" {
    for_each = lookup(each.value, "delegation", null) == null ? [] : [each.value.delegation]

    content {
      name = "delegation"
      service_delegation {
        name = delegation.value   # e.g. "Microsoft.Web/serverFarms"
      }
    }
  }
```

Leave `actions` unset unless something needs a non-default set — the provider fills the
service's required actions, and a hand-written list that disagrees with the service is
rejected at apply with a message that does not name the mismatch.

## Outputs

```hcl
output "id" { value = azurerm_virtual_network.this.id }
output "name" { value = azurerm_virtual_network.this.name }

output "subnet_ids" {
  value = { for k, s in azurerm_subnet.this : k => s.id }
}
```

A map keyed by subnet name, so a consumer writes `module.network.subnet_ids["endpoints"]`
rather than indexing a list whose order is incidental.

## Tests

Every decision in the question set, one assert each, named by its spec key path. The
values are those of a spec with `address_space: 10.42.0.0/16`, an `endpoints` subnet of
`10.42.1.0/27` and an `app` subnet of `10.42.2.0/24`; the asserts stay, the values follow
the spec. The coverage rule and the markers are in
[terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md#tests).

```hcl
run "naming" {
  command = plan

  assert {
    condition     = azurerm_virtual_network.this.name == "vnet-gwc-stg-telemetry-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

run "addressing" {
  command = plan

  # decision: virtual-network.addressing.address_space
  assert {
    condition     = length(azurerm_virtual_network.this.address_space) == 1 && azurerm_virtual_network.this.address_space[0] == "10.42.0.0/16"
    error_message = "The stated range, exactly - not rounded, not re-planned."
  }

  # decision: virtual-network.addressing.subnets
  assert {
    condition     = length(azurerm_subnet.this) == 2 && azurerm_subnet.this["app"].address_prefixes[0] == "10.42.2.0/24"
    error_message = "One azurerm_subnet per stated subnet, with its stated prefix."
  }

  # decision: virtual-network.addressing.private_endpoint_subnet_prefix
  assert {
    condition     = azurerm_subnet.this["endpoints"].address_prefixes[0] == "10.42.1.0/27" && cidrnetmask(azurerm_subnet.this["endpoints"].address_prefixes[0]) != "255.255.255.248"
    error_message = "The endpoint subnet carries the stated prefix; a /29 leaves three usable addresses."
  }

  # decision: virtual-network.addressing.dns_servers
  assert {
    condition     = length(azurerm_virtual_network.this.dns_servers) == 0
    error_message = "Azure-provided DNS: it resolves privatelink zones without setup."
  }
}

run "subnet_policy" {
  command = plan

  # decision: virtual-network.subnet_policy.private_endpoint_network_policies
  assert {
    condition     = alltrue([for s in azurerm_subnet.this : s.private_endpoint_network_policies == "Enabled"])
    error_message = "Enabled: the subnet's NSG and routes apply to endpoint traffic."
  }

  # decision: virtual-network.subnet_policy.service_endpoints
  assert {
    condition     = alltrue([for s in azurerm_subnet.this : length(s.service_endpoints) == 0])
    error_message = "No service endpoints: the weaker posture, used only where a private endpoint is not available."
  }

  # decision: virtual-network.subnet_policy.subnet_delegations
  assert {
    condition     = alltrue([for s in azurerm_subnet.this : length(s.delegation) == 0])
    error_message = "No delegation unless a service was named."
  }
}

run "security" {
  command = plan

  # decision: virtual-network.security.ddos_protection
  assert {
    condition     = length(azurerm_virtual_network.this.ddos_protection_plan) == 0
    error_message = "No DDoS plan: a platform decision, not a workload one."
  }
}

run "observability" {
  command = plan

  # decision: virtual-network.observability.diagnostic_workspace
  assert {
    condition     = azurerm_monitor_diagnostic_setting.network.log_analytics_workspace_id == azurerm_log_analytics_workspace.this.id
    error_message = "Network diagnostics route to the deployment's workspace."
  }

  # decision: virtual-network.observability.flow_logs_enabled
  assert {
    condition     = length(azurerm_network_watcher_flow_log.this) == 0
    error_message = "Flow logs off: a Network Watcher and a storage account are moving parts nobody asked for."
  }
}
```

With `observability_ownership: reference` the workspace id comes from
`var.diagnostics_workspace_id` instead, set in the test's `variables` block to a parseable id.
