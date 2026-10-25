# Public IP address - what the question set cannot express

## Fixed at creation

- **The SKU.** `Standard` and `StandardV2` are not interchangeable and a change means a new
  address - and a new value for everything that held the old one: a partner's allowlist, a DNS
  A record, a certificate's SAN.
- **The zones.** Zonal to zone-redundant (and back) is a new address, not an edit.
- **The IP version and the tier** (regional or global).
- **The region.** An address is regional and attaches only to a resource of its own region.
- **The value itself.** A `Static` address keeps it until the resource is deleted; deleting it,
  or the consumer that owned it with `delete_option: Delete`, releases it to the pool and it
  does not come back.

## Ordering

1. Resource group
2. Public IP address
3. Its consumer (NAT gateway, Application Gateway, firewall, Bastion, load balancer) - takes the
   resource id
4. The diagnostic setting, after the workspace

Deletion runs the other way, and the failure is the usual one: an address still referenced by
its consumer refuses to go, and the error names the consumer.

## What decides whether the address may exist

A public address is the clearest example of a public surface, so it is not created because a
resource asked for it. `deployment.network_exposure` decides first:

| Posture | Addresses rendered |
|---|---|
| `private` | Only outbound-only and platform-access purposes: `nat_gateway`, `firewall`, `bastion`, `vpn_gateway`. Anything else is an `overridden` exception with a reason |
| `private_with_exceptions` | The above, plus the named exceptions (`application_gateway`, `load_balancer`), each recorded |
| `public` | Whatever the system needs |

Under `network_exposure: private` an inbound address for an Application Gateway is therefore a
departure, not a default - and `landing_zone: corp` workloads normally reach the internet
through the hub, with no address of their own at all.

## Pitfalls

**The Basic SKU and Dynamic allocation are gone.** Templates copied from the Basic era carry
`sku = "Basic"` and `allocation_method = "Dynamic"`; both are retired. A Standard address is
secure by default: it accepts no inbound traffic until an NSG on the subnet or the NIC allows
it, which Basic did not.

**`StandardV2` is for one consumer.** It exists for the zone-redundant NAT gateway generation
(`nat-gateway.sku: StandardV2`). The consumers that need `Standard` (Application Gateway,
firewall, Bastion, load balancers) do not take it. The two have to match in a pair, and the
address of a NAT gateway that creates its own is a decision of the `nat-gateway` set.

**A DNS label is a public name.** `<label>.<region>.cloudapp.azure.com` is resolvable by
anyone and unique per region. It is released with the address and can be claimed by another
tenant afterwards - a dangling CNAME to it elsewhere is a subdomain takeover.

**An orphaned address is a bill.** A Standard static address is charged whether or not it is
attached. An address whose consumer was deleted stays, and nothing alerts on it; the purpose in
the name is what lets a review find it.

**DDoS "inherited" can mean unprotected.** `VirtualNetworkInherited` takes the plan of the
network the consumer sits in; when that network has none, only Azure's free infrastructure
protection applies. The address is covered as well as its network is and no better.

**Zones are per region.** `zones = [1, 2, 3]` in a region with fewer zones, or none, is rejected
at apply and not at plan.

## Not covered here, and why

Public IP prefixes and BYOIP, the public DNS zone and its records, and the consumer's own
association each carry decisions of their own; none has a question set here. A request for one
is said out loud, not improvised.
