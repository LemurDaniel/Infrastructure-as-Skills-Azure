# Rendering a virtual network peering as Terraform

Mapping from the question set to the peering. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

The peering is a **submodule of the virtual network module**:
`Azure/avm-res-network-virtualnetwork/azurerm//modules/peering` - the primary rendering. Documented
against the parent module's **v0.22.3** (resolved 2026-10-25); resolve the current version and re-read
the submodule's README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.22.0`. The Terraform index
lists the parent only (`avm-res-network-virtualnetwork`, Available); the submodule ships inside it.

**It is AzAPI only**: `azapi ~> 2.12` and Terraform `>= 1.9, < 2.0`, no `azurerm`. It takes the *local*
network as `parent_id` (the network's resource id, validated against the id pattern) and the remote as
`remote_virtual_network_id`, so neither network has to be a module output of this configuration - a
referenced hub is `{ existing: virtual_network }` in the spec, an id variable from the stage files. **One call creates both
directions** with `create_reverse_peering = true`; the reverse side has its own `reverse_*` inputs and
is created on the remote network by the same provider identity.

The network module also takes a `peerings` map for the same thing from inside the network call (see
[the network set](../virtual-network/terraform.md)); use one or the other for a given pair, never both.

**The module's defaults agree with the guardrails here** (`allow_forwarded_traffic = false`,
`allow_gateway_transit = false`, `use_remote_gateways = false`, `do_not_verify_remote_gateways = false`,
`allow_virtual_network_access = true`); the Bicep module's differ, so every value is written.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| names | `name`, `reverse_name` | From the naming provider with the `name` parameter set per side |

The module peers whole networks by default (`peer_complete_vnets = true`); the address-space and subnet
variants are not rendered.

### The call

```hcl
data "naming_name" "peering" {
  resource   = "Azure::Microsoft.Network/virtualNetworks/virtualNetworkPeerings"
  parameters = { name = "${var.workload}-to-hub" }
}

data "naming_name" "reverse_peering" {
  resource   = "Azure::Microsoft.Network/virtualNetworks/virtualNetworkPeerings"
  parameters = { name = "hub-to-${var.workload}" }
}

module "peering" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm//modules/peering"
  version = "~> 0.22.0"

  name                      = data.naming_name.peering.name
  parent_id                 = var.local_virtual_network_id
  remote_virtual_network_id = var.remote_virtual_network_id

  # decision: virtual-network-peering.peering.allow_virtual_network_access
  allow_virtual_network_access = true
  # decision: virtual-network-peering.networking.allow_forwarded_traffic
  allow_forwarded_traffic = true
  # decision: virtual-network-peering.networking.allow_gateway_transit
  allow_gateway_transit = false
  # decision: virtual-network-peering.networking.use_remote_gateways
  use_remote_gateways = false
  # decision: virtual-network-peering.networking.verify_remote_gateways
  do_not_verify_remote_gateways = false
  # whole networks only (the boundary)
  peer_complete_vnets = true

  # decision: virtual-network-peering.peering.both_directions
  create_reverse_peering = true
  reverse_name           = data.naming_name.reverse_peering.name
  # decision: virtual-network-peering.peering.reverse_allow_virtual_network_access
  reverse_allow_virtual_network_access = true
  # decision: virtual-network-peering.networking.reverse_allow_forwarded_traffic
  reverse_allow_forwarded_traffic = true
  # decision: virtual-network-peering.networking.reverse_allow_gateway_transit
  reverse_allow_gateway_transit = false
  reverse_use_remote_gateways   = false
}

output "id" { value = module.peering.resource_id }
output "reverse_id" { value = module.peering.reverse_resource_id }
```

The values shown are a spoke behind a hub with a firewall and no gateway (`central_inspection: true`,
`hub_gateway: false`). With `hub_gateway: true` and `peering_role: spoke` the spoke call has
`use_remote_gateways = true` and `reverse_allow_gateway_transit = true`; the hub's own repository
(`peering_role: hub`) has `allow_gateway_transit = true` on its side. With `both_directions: false`
`create_reverse_peering` is `false` and no `reverse_*` input is written. The reverse side is created
on the hub network: the pipeline's identity needs write rights there, which is the platform team's grant,
and in another subscription the `azapi` provider reaches it by id.

### Tests

`mock_provider "azapi"` keeps the plan credential-free; the submodule declares only `azapi` and has no
telemetry provider. It exposes **only names and ids** as outputs (`name`, `resource_id`, `reverse_name`,
`reverse_resource_id`), not the resources: the names are asserted (`module.peering.name` against
`naming.yaml`, `module.peering.reverse_name`), and whether the reverse side exists
(`module.peering.reverse_resource_id != null`, known at plan only if the mock gives it a shape).
Every switch is `# not-testable: <key> - set through the module's input; its own tests cover the
mapping`. That is the honest state; the call itself is the review.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Argument |
|---|---|
| names | `.name` |

The provider has no input for `doNotVerifyRemoteGateways` and no reverse side; a hub-and-spoke pair needs
two resources, and the second depends on the first only through the remote gateway's existence.
