# DDoS protection plan - what the question set cannot express

## The model: one plan per tenant

Azure DDoS Network Protection is sold as a **plan**: a fixed monthly fee that covers 100 public IP
addresses across every virtual network and subscription of the tenant, with a small surcharge per
address beyond. A plan is therefore platform infrastructure - the connectivity subscription owns
it, and every network that wants protection references it. That is what `ownership: platform`
renders: nothing, plus the plan's id handed to the networks. `ownership: deployment` exists for the
case without a platform (`landing_zone: standalone`) and for the platform's own render.

The alternative for a deployment with a few public addresses and no plan is **DDoS IP Protection**:
the same mitigation bought per address, without a plan resource. It is a property of the public IP
(`ddosSettings.protectionMode: Enabled` with no plan id on the ARM side) and belongs to the
`public-ip-address` set once that set carries it; today that set's `Enabled` mode expects a plan, and
IP Protection is named here so the choice is visible and not improvised.

## Fixed at creation

- **The name and the region.** Both are placement; the plan protects networks in any region.
- **Nothing else.** A plan has no properties beyond its tags.

## Ordering

1. Resource group
2. The plan - in the connectivity deployment, or in production under `stages_with_plan: production`
3. The virtual networks, each with `enableDdosProtection: true` and the plan's id
4. The public IPs that inherit from their network (`VirtualNetworkInherited`)
5. The diagnostic settings of the public IPs - the DDoS categories live there, not on the plan

Deletion runs the other way: a plan that a network still references refuses to go, and the error
names the network.

## Pitfalls

**A plan that nothing references bills and protects nothing.** The plan is the subscription to the
service; the association on the network is what protects. A render that creates the plan and
forgets the network's `ddos_protection` has paid for nothing, and nothing alerts on it.

**Two plans in one tenant are two fees.** Every plan carries the full monthly fee, whichever networks
it covers. A workload in a landing zone that creates its own plan beside the platform's is the
most expensive line on its bill. `ownership: platform` is the default for that reason, and
`stages_with_plan: production` for the same reason one level down.

**The plan is tenant-wide, the association is not.** Networks in other subscriptions of the same
tenant can reference the plan; the deploying identity needs rights on it (`role_assignments`).
A network in another tenant cannot.

**The logs are on the public IP.** `DDoSProtectionNotifications`, `DDoSMitigationFlowLogs` and
`DDoSMitigationReports` are diagnostic categories of `publicIPAddresses`, collected by the
`public-ip-address` set. The plan has no diagnostic setting and no metrics; a render that attaches
one fails at apply.

**Azure's basic protection is always on.** Infrastructure protection covers every public address
without a plan: the platform survives, the workload may not. A plan adds the per-network tuning,
adaptive thresholds, attack analytics, the rapid-response team and the cost-protection credit. The
difference is what a development stage goes without under `stages_with_plan: production`.

**The modules take the resource group by name.** Both are plain `azurerm`/ARM wrappers of a resource
with no properties; neither carries diagnostics, which is correct for this type.

## Not covered here, and why

DDoS IP Protection as a rendered mode of a public IP, the network's association, the public IP's
diagnostic categories, DDoS Rapid Response engagement and the cost-protection claim each belong to
another set or to operations; a request for one is said out loud, not improvised.
