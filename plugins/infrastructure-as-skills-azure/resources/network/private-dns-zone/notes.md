# Private DNS zone - what the question set cannot express

## When this set is used, and when it is not

In an Azure landing zone the privatelink zones are the hub's, and a workload **references** them
(`deployment.private_dns_ownership: platform`) - this set renders nothing for them. It is reached
for:

| Case | What it renders |
|---|---|
| `private_dns_ownership: deployment` (`landing_zone: standalone`, an isolated environment) | One zone per row of [private-dns-zones.md](../../../core/iac-rendering/references/private-dns-zones.md) that a resource in the spec uses, linked to the network |
| An **internal domain** of the customer's own (`zone_kind: internal_domain`) | The zone, its links and a few static records |

Which zone belongs to which endpoint is not a decision: it is that table, the same for every
deployment, and the private-endpoint set and every resource's own endpoint questions read it
too. A resource added later adds its row to `wiring.private_dns_zones`; a list built from the
first resource only is the usual reason a second endpoint resolves to nothing.

## Fixed at creation

- **The zone's name.** It is the domain; a different name is a different zone.
- **The links' names.** A link cannot be renamed; its network can not be changed either.
- **Nothing about records.** They are edited in place, which is why a static list is reviewed.

## Ordering

1. Resource group, then the virtual network(s)
2. The zone
3. The virtual network links - they need both
4. Static records of an internal domain
5. The private endpoints that attach to the zone - last; an endpoint created before the zone
   has nowhere to write its record

Deletion runs the other way. A zone with links, or with records written by an endpoint's zone
group, refuses to go until they are removed; the error names the child rather than the
dependency chain.

## Pitfalls

**A zone without a link resolves nothing.** The zone exists, the endpoint's record is in it, and
a machine in a network that is not linked gets the target's public address. Every network that
must reach an endpoint by name needs a link - or forwards to a resolver in one that has.

**Linking the zone changes the whole network's answers.** Once a privatelink zone is linked, every
name of that service in the network is answered by the zone alone. A resource of the same type
that has no endpoint (a SaaS account, another team's storage) returns NXDOMAIN. The fallback
`resolution_policy: NxDomainRedirect` sends those names to public DNS; it is a decision, not a
default.

**One writer per record.** An endpoint's zone group, the platform's policy and a static record in
this set are three writers; for a privatelink zone only the first or the second is right. A
`static_records` entry in a privatelink zone is a plan that never stops showing drift.

**Auto-registration is exclusive.** A network can have auto-registration on one zone only, and
that zone then cannot be a privatelink zone. It registers virtual machines, not endpoints and not
App Service.

**The module's `Default` resolution policy renders no value.** AVM Terraform sends
`resolutionPolicy = null` for `Default` and the value only for `NxDomainRedirect`; the plan shows
the absence, and the API fills `Default`.

**Names differ by cloud and sometimes by region.** `privatelink.<region>.azurecontainerapps.io`
and the backup zone carry a region or a code; the sovereign clouds use other suffixes. Look the
row up in the Microsoft Learn page `private-dns-zones.md` cites rather than editing a name by
hand.

**Records show private addresses.** A zone and its records are visible to every identity with read
access on the group. They name the private addresses of the deployment's resources: the group
is chosen with that in mind.

## Not covered here, and why

DNS Private Resolver and its rulesets, conditional forwarders, split-horizon namespaces,
public DNS zones and records, and DNS security policies each carry decisions of their own; none
has a question set. A request for one is said out loud, not improvised.
