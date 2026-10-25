# Bastion - what the question set cannot express

## Fixed at creation

- **The zones**, and the public IP's. A Bastion without them does not gain them.
- **The subnet and its name.** `AzureBastionSubnet`, a /26 or larger, holding nothing else. The
  Developer SKU has no subnet and attaches to the virtual network.
- **Public or private-only.** `enablePrivateOnlyBastion` is part of the host's shape (Premium); moving a
  public Bastion to a private-only one is a rebuild with the network security group changed to match.
- **The SKU moves up, not down.** Basic to Standard to Premium is an in-place change (with downtime for
  the host); lowering it is a rebuild.
- **The name** and the region.

## Ordering

Resource group, virtual network with `AzureBastionSubnet`, its network security group (the documented
rule set, before the host: a missing rule fails the deployment late), the public IP (Standard, static,
zone-redundant), the Bastion, then the role assignments that let people use it (Reader on the Bastion,
the machine and its network interface; the Virtual Machine Login role for Entra sign-in). Creating a
Bastion takes about ten minutes; deleting its subnet before it is gone fails.

## Pitfalls

**The subnet's network security group is a fixed list.** Inbound 443 from the internet (or the users'
range), 443 from `GatewayManager`, 443 from `AzureLoadBalancer`, and 8080 and 5701 between bastion
hosts; outbound 22 and 3389 to the virtual network, 443 to `AzureCloud`, and 8080 and 5701 to the
virtual network, plus the HTTP session-information outbound. A `Deny all` inbound that does not name
the service tags leaves a Bastion that deploys and then cannot connect to anything. The rule set is
the network security group set's; this one only expects it.

**A Bastion reaches what its network reaches.** Same virtual network or a peered one (Standard and above
also across a global peering), so the peering has to exist and allow traffic before a machine in a
spoke can be reached. A Bastion in the hub serves every peered spoke; one per spoke is the expensive
shape, and the landing zone answer is the shared one.

**Shareable links are access without a sign-in.** Anyone holding the link opens a session in a browser;
there is no portal login and no RBAC check. The audit log records the connection, not who the link
holder is. Off, and a named exception per use if ever on.

**IP-based connection and the native client widen the reach, not just the convenience.** An address
connection ignores the "machines I have a role on" boundary for everything routable from the
Bastion's network, including on-premises hosts; the native client puts a tunnel on the user's device.
Both are Standard and above and both off.

**A private-only Bastion locks out whoever is not on the private connection.** It has no public address;
users reach it over VPN or ExpressRoute into the virtual network. A support engineer on a hotel
network cannot, and the break-glass path has to exist before the public one is removed.

**Basic and Standard are different products.** Basic is two fixed instances for browser sessions; the
scale units, the native client, IP connect, file copy and the switches in the question set do not exist
below Standard, and the modules reject or ignore them there. Developer is a shared, per-session
resource with no network integration.

**Recording needs a storage container.** Session recording on Premium writes to a container reached
through a SAS URL configured on the Bastion in the portal; neither module carries it. It is a key to
hold, rotate and put in Key Vault, and its owner is named in the handover.

**The two modules disagree.** The Bicep module cannot set the native client or metrics and defaults file
copy on and zones off; the Terraform module carries all of them and defaults file copy off and zones on.
A spec rendered to both lands on the same decisions only because every value is written.

**Terraform: the lock-in is on `azurerm` 4.x.** The module constrains it to `~> 4.10`, so a root that
wants it cannot be on 5.x, and the authored fallback in that root follows 4.x.

## Not covered here, and why

Kerberos authentication, the session-recording storage container, a Bastion in a virtual WAN hub,
the network security group of `AzureBastionSubnet` (it has its own set), and the role assignments that
make Bastion usable for a person each carry decisions of their own and have no question set here; a
request for one is said out loud, not improvised.
