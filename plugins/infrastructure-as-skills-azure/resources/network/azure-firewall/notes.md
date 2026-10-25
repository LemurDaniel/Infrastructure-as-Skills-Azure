# Azure Firewall - what the question set cannot express

## Fixed at creation

- **The availability zones.** A firewall without zones does not gain them; it is rebuilt.
- **The management NIC** (forced tunneling, and always on `Basic`). Part of the firewall's shape; adding
  it later means deallocating or rebuilding the firewall.
- **The subnet and its name.** `AzureFirewallSubnet` and `AzureFirewallManagementSubnet` are fixed names,
  each a /26 at least and holding nothing else.
- **The SKU name** (`AZFW_VNet` against `AZFW_Hub`) and the region. The tier moves in a maintenance
  window, together with the policy's tier.

## Ordering

Resource group, virtual network with both firewall subnets, public IPs (zone-redundant, Standard,
static), the firewall policy, the rule collection groups, the firewall, then the peerings to the spokes,
then the spokes' route tables (`0.0.0.0/0` to the firewall's private IP, with "propagate gateway
routes" off) and their DNS setting (the firewall's private IP, when the DNS proxy is on). Creating or
updating a firewall takes ten minutes or more; a policy update is applied without touching the firewall.

## Pitfalls

**A firewall nobody routes through filters nothing.** The traffic only reaches it through a route table
on the spoke subnets, and that table is not this set's. A deployment can be green and unprotected.

**Asymmetric routing breaks connections.** Return traffic that does not pass the firewall it came
through is dropped. The usual cause is a spoke that is reachable by a second path (a peering to
another spoke, a gateway route) while the default route points at the firewall.

**The DNS proxy and custom DNS servers have to agree.** With the proxy on, the spokes use the firewall
as their DNS server and the firewall forwards to Azure or to the listed resolvers. A spoke that keeps
Azure-provided DNS resolves fine but a network rule that names an FQDN is then matched against an
answer the firewall never saw, and fails intermittently.

**SNAT port exhaustion looks like timeouts.** Each public address carries a fixed number of source ports
per backend instance. The `SNAT port utilization` metric is the alert; a second address is the fix, a
NAT gateway on the firewall subnet the better one for a very chatty workload.

**Structured logs need the dedicated destination.** The `AZFW*` categories write into their own tables
only with `log_analytics_destination_type = Dedicated`; with `AzureDiagnostics` they land in one wide
table, and the workbooks and the queries written for them find nothing. The legacy `AzureFirewall*Rule`
categories are the ones that work with the old destination type, and are not collected here.

**Rules are processed by priority, and DNAT first.** Rule collection groups by priority, inside a group
DNAT then network then application collections. A broad network rule at a lower number hides an
application rule behind it, and the log then names the network rule.

**Threat intelligence in `Deny` blocks before the rules run.** A legitimate destination that lands on the
feed is blocked whatever the allow rules say; the allowlist on the policy (FQDNs and addresses) is the
remedy, set with the feed's entry in the ticket.

**Premium features cost time, not just money.** TLS inspection needs the CA certificate trusted on every
client, per-category exemptions, and a plan for the certificate's expiry. Intrusion detection in `Deny`
needs a week in `Alert` to find the false positives. The tier alone switches neither on.

**Terraform: the lock-in is on `azurerm` 4.x.** The firewall and policy modules constrain it below 5.0,
so a root that wants them cannot be on 5.x, and the authored fallback in that root follows 4.x.

## Not covered here, and why

Virtual WAN secured hubs and the Firewall Manager, the firewall's own autoscale limits, IP groups, the
web categories and URL filtering rules of Premium, a NAT gateway on the firewall subnet, the flow trace
and fat-flow logs, and the route tables that steer traffic into the firewall each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
