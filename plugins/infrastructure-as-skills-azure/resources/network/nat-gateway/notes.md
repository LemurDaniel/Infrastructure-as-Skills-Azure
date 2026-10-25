# NAT gateway - what the question set cannot express

## Fixed at creation

- **The SKU.** `Standard` to `StandardV2` (or back) is a new gateway, and with it new outbound
  addresses - which is what a partner has allowlisted.
- **The zone** of a `Standard` gateway.
- **The region**, and the virtual network: a gateway serves subnets of one network.
- **The addresses' SKU and zones** when the gateway creates them: they have to match the gateway.

## Ordering

1. Resource group
2. Public IP addresses (created with the gateway, or the `public-ip-address` set's)
3. NAT gateway
4. Subnet association - the subnet takes the gateway's id, so it is made in the virtual-network
   set (`nat_gateway` on a subnet), in the same deployment or after

A gateway created after its subnet changes nothing until someone associates it. Deletion runs the
other way: a gateway still associated with a subnet refuses to go, and an address still used by
the gateway refuses to go. The association is removed first.

## What it does, and what it replaces

A NAT gateway gives every machine in its subnets one owned, static set of outbound addresses and
a large pool of SNAT ports. It is **outbound only**: it never accepts a connection from outside,
and replies belong to connections a machine started.

| Without a NAT gateway | With one |
|---|---|
| A subnet's outbound traffic uses Azure's implicit default outbound address - shared, not owned, and being retired for new networks | The gateway's addresses, which the customer owns and can give to a partner |
| A load balancer's or a VM's own address, with a small fixed SNAT port allotment | A pool of ports per address across all machines of the subnets |
| Egress through the firewall, when a route table says so | The gateway - **but not together with that route**, below |

## Pitfalls

**A default route to a firewall overrides the NAT gateway.** A subnet whose table sends
`0.0.0.0/0` to a virtual appliance (`route-table.default_route: firewall`) goes through the
appliance, and the NAT gateway is not used for it. In a hub-and-spoke platform the NAT gateway
belongs on the firewall's own subnet, to give the firewall more SNAT ports; the platform owns that
subnet. A spoke asks for a NAT gateway only when it has no forced tunnelling (`default_route: none`).

**One gateway per subnet, one network per gateway.** A subnet cannot have two; two subnets can share
one; a subnet in another network cannot use it.

**Some subnets do not take one.** `GatewaySubnet`, `AzureFirewallSubnet` and `AzureBastionSubnet` have
their own egress.

**The zone is a commitment.** A zonal `Standard` gateway in zone 1 serves a machine in zone 2 across
a zone boundary, and the loss of zone 1 ends outbound connectivity for all of them. `StandardV2`
removes the question; it needs `StandardV2` addresses and is not in every region.

**Port exhaustion looks like a flaky application.** Each address provides about 64,000 ports to one
destination address and port. Many connections to one backend (a database, an API) use them up;
the symptom is intermittent failed connects and the `SNAT Connection Count` metric showing failures.
More addresses, a shorter idle timeout or connection pooling in the client are the fixes, in that order of
cost.

**The addresses are a handover item.** The partner's firewall allowlist needs them, and a recreated
gateway without separately managed addresses (`public_ip_source: separate`) changes them.

**Idle timeout is per gateway,** not per address; the addresses created with the gateway carry
a timeout of their own that is not used for NAT traffic (the Terraform module's default for it is 30).

## Not covered here, and why

Public IP prefixes (beyond referencing one), the firewall that sits beside it, the platform's
hub egress design, outbound rules of a load balancer and a virtual network's `defaultOutboundAccess`
each carry decisions of their own; none has a question set. A request for one is said out loud,
not improvised.
