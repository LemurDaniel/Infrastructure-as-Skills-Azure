# Azure network resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table — the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| virtual network, vnet, address space, subnets | `virtual-network/questions.yaml` | [notes](virtual-network/notes.md) |
| network security group, NSG, security rules | `network-security-group/questions.yaml` | [notes](network-security-group/notes.md) - the subnet association is the virtual-network set's |
| Application Gateway, WAF, web application firewall, layer-7 load balancer, ingress for a vnet, reverse proxy for web apps | `application-gateway/questions.yaml` | [notes](application-gateway/notes.md) - v2 only, firewall policy as its own resource |
| Front Door, CDN, global load balancer, edge, global WAF | `front-door/questions.yaml` | [notes](front-door/notes.md) - Standard and Premium; classic CDN is not covered |
| peering, VNet peering, hub and spoke, spoke, gateway transit, forwarded traffic | `virtual-network-peering/questions.yaml` | [notes](virtual-network-peering/notes.md) - both directions, route tables are separate |
| Azure Firewall, firewall policy, DNS proxy, threat intelligence, IDPS, TLS inspection, egress filtering, hub firewall | `azure-firewall/questions.yaml` | [notes](azure-firewall/notes.md) - VNet firewall plus policy; a spoke deployment peers to the platform's hub firewall and does not create one |
| load balancer, internal load balancer, public load balancer, ILB, layer-4, health probe, backend pool, outbound rule, NAT rule | `load-balancer/questions.yaml` | [notes](load-balancer/notes.md) - Standard regional only; Basic is retired, Gateway and global tier are not covered |
| Bastion, Azure Bastion, jump host, RDP/SSH without public IP, AzureBastionSubnet | `bastion/questions.yaml` | [notes](bastion/notes.md) - `AzureBastionSubnet` is the network set's; the subnet's NSG rules are the NSG set's |
| public IP, public IP address, PIP, static IP, outbound IP, DNS label | `public-ip-address/questions.yaml` | [notes](public-ip-address/notes.md) - Standard and StandardV2 only; consumers take the id |
| private endpoint, private link, privatelink, subresource, group id | `private-endpoint/questions.yaml` | [notes](private-endpoint/notes.md) - standalone form; a resource whose module has `private_endpoints` renders its own |
| private DNS zone, privatelink zone, vnet link, auto-registration, internal DNS | `private-dns-zone/questions.yaml` | [notes](private-dns-zone/notes.md) - the platform owns the privatelink zones unless `private_dns_ownership: deployment` |
| route table, UDR, user-defined route, forced tunneling, default route, BGP propagation | `route-table/questions.yaml` | [notes](route-table/notes.md) - the subnet association is the virtual-network set's |
| NAT gateway, outbound, SNAT | `nat-gateway/questions.yaml` | [notes](nat-gateway/notes.md) - outbound only; overridden by a default route to a firewall |
| public DNS zone, DNS zone, domain, name servers, delegation, DNSSEC, A record, CNAME, TXT record, MX, CAA, öffentliche DNS-Zone, Domäne, Nameserver | `public-dns-zone/questions.yaml` | [notes](public-dns-zone/notes.md) - the domain is the name; delegation at the registrar is an open entry of the domain owner; privatelink zones are the private-dns-zone set's |
| Traffic Manager, DNS load balancing, DNS failover, geo routing, multi-region failover, active-passive regions, priority routing, weighted routing, trafficmanager.net, Lastverteilung per DNS, Failover zwischen Regionen | `traffic-manager/questions.yaml` | [notes](traffic-manager/notes.md) - DNS-level steering only; a WAF, TLS or path routing request goes to front-door |
| DDoS, DDoS protection plan, DDoS Network Protection, DDoS-Schutz, Schutzplan | `ddos-protection-plan/questions.yaml` | [notes](ddos-protection-plan/notes.md) - one plan per tenant, referenced by a workload; the vnet association is the virtual-network set's; IP Protection is the per-address alternative |
| Network Watcher, flow logs, VNet flow logs, NSG flow logs, traffic analytics, connection monitor, Verkehrsaufzeichnung, Flow-Logs | `network-watcher/questions.yaml` | [notes](network-watcher/notes.md) - references Azure's auto-created watcher; renders VNet flow logs into NetworkWatcherRG; NSG flow logs are retired and not rendered |

When a question set does not exist yet, say so rather than improvising one. Generating a
resource without its decision set is how this plugin loses the property that makes it worth
using. Fall back to [the guardrails](../../core/iac-authoring/references/guardrails.md),
generate from those rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) — the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers `network_ownership` and the address space before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) — the spec into Terraform or Bicep

## True for the whole family

**The address space is the one decision that cannot be fixed later.** Every other property
of a network is editable in place; its range is not, because every subnet carved out of it
has to be emptied and rebuilt. A guess that nobody rejected is still a guess — ask the
owner, or record it as `open` and stop.

**A subnet is not an independent resource in practice.** Azure lets you manage subnets
inline in the vnet or as separate resources, and mixing both in Terraform makes the two
fight on every apply — `azurerm_subnet` plus a `subnet` block in `azurerm_virtual_network`
is the classic plan-churn bug. Pick one per configuration; this family renders them as
separate resources.

**Deleting a subnet that holds a private endpoint fails**, and the error names the
endpoint rather than the dependency. Ordering is the thing to get right the first time.

**Service endpoints and private endpoints are not two strengths of the same thing.** A
service endpoint keeps the resource publicly addressable and an ACL refuses traffic; a
private endpoint removes the public surface. The posture ladder is in the guardrails.

## Adding a resource to this family

Same steps as any family — see
[iac-authoring](../../core/iac-authoring/SKILL.md#adding-a-resource). Do **not** add a
skill for it: the listing budget is shared, and azure-resources is the triggering unit. If the
resource brings a term people would type that the
[azure-resources](../../core/azure-resources/SKILL.md) description lacks, add it there.
