# Public DNS zone - what the question set cannot express

## Fixed at creation

- **The zone's name.** It is the domain; a different name is a different zone.
- **The name servers.** Azure assigns four per zone at creation. A deleted and recreated zone gets
  a different set, and every NS record and DS record that pointed at the old one - at the registrar,
  in a parent zone - is wrong until somebody updates it. That is why the zone carries the
  `deployment.resource_lock` lock and why a rename is never "just recreate".
- **Nothing about records.** They are edited in place, which is why the lists are reviewed.

## Ordering

1. Resource group
2. The zone - production's apex first, the stages' child zones in their own stages
3. Read the name servers (`name_servers` / `nameServers` output)
4. **Outside Azure**: the registrar's NS records (apex) or the parent zone's NS record set (child
   zone, `child_zone_delegations` of the parent) - the `open:` entry owned by `registrar_owner`
5. The verification records, before the resources that check them (App Service custom domain,
   Front Door domain validation): the check fails and the resource deployment with it when the
   TXT is not there yet
6. DNSSEC: enable, read the DS record (`az network dns dnssec-config show`), publish it at the parent
7. The record sets and aliases that point at resources created by the same deployment - last,
   because an alias needs the target's id

Deletion runs the other way, and step 6 is the one that bites: **remove the DS record at the
registrar first**, wait a TTL, then disable DNSSEC or delete the zone. The other order leaves a
chain of trust pointing at keys that no longer exist, and validating resolvers return SERVFAIL for
the whole domain.

## The stage model

A domain exists once. The default stack therefore renders:

| Stage | `zone_name` | `child_zone_delegations` |
|---|---|---|
| production | `example.com` | `dev` → the development zone's name servers, `test` → the test zone's |
| test | `test.example.com` | none |
| development | `dev.example.com` | none |

The child zones are deployed first and their name servers read, then the production zone's
delegation list is filled. A `[sandbox]` stack is one zone, usually a child of a domain the customer
already runs elsewhere - the delegation is then at that provider, not in Azure.

## Pitfalls

**A zone without a delegation answers nobody.** The zone exists, the records are right, and the
world still asks the registrar's old name servers. Nothing in Azure fails; the failure looks like a
DNS problem elsewhere. The name servers are an output and the delegation an `open:` entry until
the owner confirms it.

**DNSSEC is safe to turn on and dangerous to turn off.** Signed without a DS at the parent, the
zone is as reachable as before. Signed with one, disabling DNSSEC or deleting the zone before the DS
is removed takes the domain offline for every validating resolver. The handover carries the order.

**One writer per record.** A TXT record that the wiring writes (`verification_records`) and the same
name typed into `record_sets` are two owners of one record set and a plan that never stops showing
drift - in Terraform both are `azurerm_dns_txt_record` with the same name, and the second apply
fails with a conflict. The wiring owns the proof records, the customer's list owns the rest.

**TXT values longer than 255 characters are split.** A DKIM key is written as several strings in one
record; both modules take a list of strings per value and the resolver joins them.

**The Terraform module repeats the zone in every record.** Each record object carries
`resource_group_name` and `zone_name` of its own; the reference merges them in from one local so
that a record cannot point at a zone other than the one the call creates.

**CNAME at the apex is not allowed.** `@` cannot be a CNAME; the apex points at a Front Door or a
Traffic Manager profile through an **alias A/AAAA record** (`targetResourceId`), which is what the
alias form in `record_sets` is for.

**Records are public.** Everything in the zone is visible to anyone who asks, including the TXT
records that name the services the domain uses. A record for an internal host belongs in a private
zone.

**Query volume is the bill.** A zone costs cents per month plus per million queries; a 60-second TTL
on a busy name multiplies the queries. `record_ttl_seconds` is the default and an entry may lower
it for a move.

## Not covered here, and why

Private DNS zones (`private-dns-zone`), Traffic Manager and Front Door as alias targets, DNS
security policies and traffic rules, the DNS Private Resolver, domain registration itself and
split-horizon setups each carry decisions of their own; a request for one is said out loud, not
improvised.
