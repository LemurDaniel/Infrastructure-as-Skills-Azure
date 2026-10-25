# Application Gateway - what the question set cannot express

## Fixed at creation

- **The subnet.** A gateway cannot move to another subnet, and its subnet may hold nothing else.
- **The SKU family.** v1 to v2 is a migration, not an edit; v1 is retired. Between `Standard_v2`
  and `WAF_v2` the change is in place.
- **The availability zones.** Set at creation; a gateway without zones does not gain them.
- **The name** and the region.

## Ordering

Public IP (zone-redundant, Standard, static), the subnet with its network security group,
identity and the certificates in Key Vault with the identity's role, the WAF policy, the
gateway, then DNS pointing at the frontend, then the backends' own access rules that admit only
the gateway's subnet. Creating or updating takes tens of minutes.

## Pitfalls

**The subnet's network security group.** It must allow inbound `GatewayManager` on ports
65200-65535 (v2) and the `AzureLoadBalancer` probe; a rule that forgets them fails the
deployment late or leaves the gateway unhealthy. A `Deny all` inbound that does not name them
breaks it.

**One gateway, one subnet, one address budget.** Each instance takes an address and autoscale
to 125 instances needs a /24. A /27 works until the day it scales out.

**A private-only gateway is a feature, not a flag.** A gateway with no public IP needs the
subscription registered for the private application gateway feature, and network rules for the
control-plane traffic. Without it the portal and the API refuse a gateway with a private
frontend only. A public gateway with an additional private frontend always works.

**Certificates are read by identity, and expire silently.** The gateway reads the Key Vault
secret with its user-assigned identity; a certificate renewed in Key Vault is picked up (an
unversioned secret id), an expired one takes the site down. Say who renews it in the handover.

**Detection is not protection.** A firewall left in `Detection` records attacks and lets them
through. Use it for the first week of a new rule set with an owner and a date, then move to
`Prevention`.

**Health probes decide what is reachable.** A backend that fails its probe leaves the pool
silently; with all backends out the gateway answers 502. Probe path, host and status range are
the pattern's, and the `UnhealthyHostCount` metric is the alert.

**Backend TLS needs a certificate it trusts.** `backend_protocol: Https` with a self-signed or
private-CA certificate on the backend needs that root added to the gateway; a public CA
certificate needs nothing. The host-name override and SNI on the backend setting are a frequent
source of 502.

**Application Gateway is not Front Door.** Regional, in the network, one region per gateway.
For several regions, or a CDN, Front Door sits in front and the gateway behind it, reached over
a private link.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <gateway id>` before a render.

## Not covered here, and why

Application Gateway for Containers (a separate resource), the v1 SKUs, mutual TLS client
certificate chains, URL rewrite rule sets, custom error pages, WebSocket and gRPC tuning, and
the per-site firewall policies each carry decisions of their own and have no question set; a
request for one is said out loud, not improvised.
