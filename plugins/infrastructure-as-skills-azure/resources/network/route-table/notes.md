# Route table - what the question set cannot express

## Fixed at creation

- **The region.** A route table associates only with subnets of its own region.
- **A route's name.** Unique in the table; a different name is a delete and a create, and
  the subnets briefly lose the route in between.
- **Nothing else.** Routes, next hops and the propagation flag are edited in place, which is
  why they are reviewed as code - and why a wrong next hop reaches production traffic at the
  next apply.

## Ordering

The route table before the subnet that takes it: the subnet carries the table's resource id, so
the association is made in the virtual-network set (`route_table` on a subnet), in the same
deployment or after. A table created after its subnet routes nothing until someone associates it.
The firewall (or appliance) the default route points at must exist and have its rules before the
association, or the subnet loses egress the moment it is applied.

Association is made **once**: the AVM Terraform module has a `subnet_resource_ids` input that
also associates, and the virtual-network module has `subnets.<k>.route_table` - using both makes
each apply undo the other. This family associates in the virtual-network set.

## System routes, learned routes and yours

A subnet's effective routes are the union of three sources, and the **longest prefix wins**
whatever the source; at equal prefix a user-defined route beats a BGP route, which beats a system
route.

| Source | Example |
|---|---|
| System | The virtual network's own range, peerings, `0.0.0.0/0` to the internet |
| BGP (VPN / ExpressRoute gateway), when propagation is on | `192.168.0.0/16` from on-premises |
| User-defined (this table) | `0.0.0.0/0` to the firewall |

A default route to the firewall therefore does **not** override a more specific system or learned
route: traffic to a peered network or a gateway-learned prefix goes straight there, past the
firewall, unless the table has an equally specific route. That is the design behind
`bgp_route_propagation: disabled` and behind the exceptions in `routes`.

## Subnets with requirements of their own

| Subnet | Rule |
|---|---|
| `GatewaySubnet` | Keep BGP propagation `enabled`; no `0.0.0.0/0` to an appliance - it breaks the gateway's own control traffic |
| `AzureFirewallSubnet` | If forced tunnelling is used, the firewall's own egress needs `0.0.0.0/0` to `Internet` in its table, and the management subnet its own; the platform owns this subnet |
| `AzureBastionSubnet` | A default route to an appliance is not supported; leave the table off |
| Subnets of platform services (API Management, Container Apps with workload profiles, SQL managed instance) | The service documents the routes it needs for its control plane (service tags with `Internet`); a `0.0.0.0/0` without them breaks the service |
| The private endpoint subnet | Applies to endpoint traffic only with `private_endpoint_network_policies: Enabled` (virtual-network set); then the firewall has to allow and route the replies symmetrically |

## Pitfalls

**Asymmetric routing is silent.** A UDR sends the packet out through the firewall; the reply
comes back by the peering or the gateway, directly. The firewall never sees the reply and drops
the session. Both directions need the route: the hub's table or the spoke's return routes.

**A wrong next-hop address is a total egress outage.** The address is the firewall's private IP
in the hub, an input from the platform. It is not validated by Azure at apply, and the first
symptom is timeouts in the application.

**`0.0.0.0/0` to `None` is a black hole by design,** and `Internet` as the next hop for a service
tag is how the control-plane exceptions are written. The two are not interchangeable.

**Service tags in `address_prefix` change.** `AzureBackup`, `ApiManagement` and the like follow the
service's addresses, which a literal range does not; prefer the tag, and check that the module
version accepts it as a prefix.

**Route propagation is per table, not per route.** One flag decides it for every subnet that uses
the table; a subnet that must follow BGP gets a table of its own.

**Policy and AVNM can own the association.** A DeployIfNotExists policy or Azure Virtual Network
Manager `ManagedOnly` routing may attach a table out of band; the subnet's route table is then
theirs, and setting it here as well is the drift described above.

## Not covered here, and why

Virtual WAN routing, Azure Virtual Network Manager configurations, route servers, route filters
and a firewall (rules, policy, SKU) each carry decisions of their own and have no question set;
a request for one is said out loud, not improvised.
