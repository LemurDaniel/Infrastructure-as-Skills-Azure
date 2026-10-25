# Load Balancer - what the question set cannot express

## Fixed at creation

- **The SKU and the tier.** Standard against Basic (retired) or Gateway cannot be switched in place;
  neither can regional against global.
- **The frontend's zones**, and its public IP's. A frontend without zones does not gain them.
- **The kind** (public or internal). A frontend is a public address or a subnet address; moving a
  balancer from one to the other is a rebuild with a new address.
- **The region and the virtual network of the backends.** Every member of a pool is in one network of
  the balancer's region.

## Ordering

Public IP (Standard, static, zone-redundant) or the subnet with its network security group, the
balancer with its pools and probes, the rules, then the backends joining the pools (a scale set's
network profile, a NIC's pool membership), then DNS pointing at the frontend. Deletion runs the other
way: a pool with members refuses to go, and the error names the member.

## Pitfalls

**A Standard balancer is closed.** Nothing reaches a backend until a rule exists *and* the backends'
network security group allows the traffic, and the probe needs `AzureLoadBalancer` allowed as well. A
`Deny all` inbound that does not name the service tag takes every backend out of the pool at once, and
the symptom is "the application is down", not a rule violation.

**Standard backends have no outbound path of their own.** Default outbound access is being retired, so
a backend that must call out needs an explicit way: the platform's firewall through a route, a NAT
gateway on its subnet, or an outbound rule on a public balancer. The question set sends it to the
firewall and gives the balancer none.

**A health probe that always answers is worse than none.** An HTTP probe to `/` of a web server that
returns 200 while its database is down keeps a broken backend in the pool. The probe path is the
application's own health endpoint; the `DipAvailability` metric (health probe status) is the alert.

**An internal balancer cannot be reached from a backend through itself.** A backend that connects to the
balancer's frontend and is itself chosen to answer gets its own packet back and the connection hangs.
This is a hairpin case of internal balancers; the fix is a different frontend or an application-level
address, not a rule change.

**Floating IP is for two cases.** A SQL Server Always On listener and a network appliance. Anywhere else
it makes the backend see the balancer's address as its destination and answer on an address it does
not own.

**Idle timeout and keep-alives.** TCP connections idle for four minutes by default are reset (with
`tcp_reset`) or dropped. A long-lived connection that is idle (a database pool, a websocket) sends
keep-alives under that, or the rule's timeout is raised to 30 minutes; the balancer's rule is the lever,
the application's setting is the real fix.

**One balancer per public and internal use.** A balancer is public or internal; a workload that needs
both has two. Mixed traffic through one balancer's single frontend is not a pattern Azure supports.

**Naming.** The abbreviation is `lbi` for an internal and `lbe` for a public balancer; the Terraform
render picks the kind of the `naming_name` data source, the Bicep one the variable.

**Terraform: the lock-in is on `azurerm` 4.x.** The module constrains it below 5.0, so a root that wants
it cannot be on 5.x, and the authored fallback in that root follows 4.x.

## Not covered here, and why

The Gateway SKU, the global tier (cross-region), IPv6 frontends, public IP prefixes on a frontend, inbound
NAT pools for scale sets, HA ports rules (an internal balancer for an appliance), the zone choice of
single backends and the network security group of the backends' subnet each carry decisions of their
own and have no question set; a request for one is said out loud, not improvised.
