# Virtual network peering - what the question set cannot express

## Fixed at creation

- **Which two networks.** A peering is bound to its two networks; pointing it elsewhere is a new peering.
- **Whole network against a subset.** Changing between peering the complete networks and selected
  address spaces or subnets is a rebuild; this family peers whole networks.
- **The name** of each side. Most settings can be edited in place, but a peering whose address space
  or gateway setup is wrong is easier deleted than repaired.

## Ordering

Both networks exist and their address spaces do not overlap, then (with a hub gateway) the **hub side
first**, because the spoke side's `use_remote_gateways` is refused until the hub offers transit; then the
spoke side; the state of each reads `Connected` only when both exist. A route table that sends the
spoke through the hub firewall comes after the peering, not before: a route to a next hop that is not
reachable yet blackholes the subnet. Deletion runs the other way, spoke side first.

## Pitfalls

**A peering that is `Initiated` is not a connection.** One side alone shows `Initiated` and carries no
traffic; the deployment is green and nothing is reachable. `both_directions: false` makes that a plan,
with an owner for the other side; any other time it is a bug.

**Peering is not transitive.** Spoke A peered to the hub does not reach spoke B through it. It needs a
firewall or virtual appliance in the hub doing the forwarding, a route table on each spoke pointing at
it, and `allow_forwarded_traffic` on both sides of both peerings. Missing the switch on one side gives
one-way traffic: requests arrive, replies are dropped.

**Overlapping address spaces refuse the peering at apply time**, and only then. The check is the
address plan (`deployment.address_space`); a hub that later gets an additional address space needs a
resync of every peering to it (`sync remote address space`) before the new range is routed - neither
module does this on its own, and the symptom is a new hub subnet nobody can reach.

**Gateway transit is a pair, and set on one side only.** `allow_gateway_transit` on the hub,
`use_remote_gateways` on the spoke; a spoke with a gateway of its own cannot use the hub's, and both
sides set the same way is rejected. The hub's gateway must exist before the spoke asks.

**`allow_forwarded_traffic` is not security by itself and not the route.** It lets the peer vouch for
traffic with other source addresses; the user-defined route on the spoke is what sends traffic to the
firewall. A spoke without the route filters nothing, with or without the switch.

**Cross-subscription peerings need rights on both ends.** The identity that creates the
reverse side needs the peering write on the hub network (`Network Contributor` on it, or the narrower
peering-write and `virtualNetworks/peer/action` rights); a peering across tenants additionally needs an
identity that is known in both. The error says authorisation on the remote scope, and the platform team
is the one who grants it.

**Global peering is regional billing at both ends.** A remote network in another region peers fine but
the data crossing is billed in and out.

**DNS follows the peering only if it is configured.** A peering carries packets, not name resolution:
privatelink zones reach a spoke through the hub's zone links or its DNS proxy, and the spoke's DNS server
setting points at the hub's resolver or the firewall.

**Terraform: the submodule is AzAPI only.** No `azurerm` provider is involved, so a root that calls
only the peering is free of the `azurerm` 4.x lock that the other modules of this family carry.

## Not covered here, and why

Subset peering (address spaces or subnets), IPv6-only peering, Azure Virtual Network Manager connectivity
configurations and hub-and-spoke topologies built from them, virtual WAN hub connections, the route
tables that make a peering useful, and the sync of a changed remote address space each carry decisions
of their own and have no question set; a request for one is said out loud, not improvised.
