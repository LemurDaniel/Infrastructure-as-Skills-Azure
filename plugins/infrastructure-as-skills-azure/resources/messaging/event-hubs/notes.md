# Event Hubs - what the question set cannot express

## Fixed at creation

- **Partition count** of an event hub: fixed on Basic and Standard, only raisable on Premium,
  never lowerable. It caps the number of parallel readers of a consumer group for the life of
  the hub; a different count is a new hub and a cut-over.
- **The tier, in part.** Basic to Standard is possible; Premium is a new namespace.
- **The name.** Global, 6-50 characters, letters, digits and hyphens, must start with a letter.
- **Double encryption** (`requireInfrastructureEncryption`).
- **The region.**

## Ordering

Identity, key vault and key (customer-managed key only), the storage account and container
(Capture only), the namespace, the event hubs, then consumer groups, then role assignments
(a data-plane role on an event hub needs it), then the consumers. The workspace before the
diagnostic setting. A geo pairing is the last step and needs an empty secondary.

## Pitfalls

**Events are not a queue.** A consumer reads a position in a retained stream; reading does not
remove anything. Two readers that must both see every event need two consumer groups, and a
reader that shares a group with another splits the partitions with it. Retention, not
consumption, deletes events.

**A private namespace is at least Standard.** Basic has no private endpoint or firewall. A
deployment with `network_exposure: private` that asked for Basic gets Standard, recorded as
forced.

**Retention is capped by tier.** One day on Basic, seven on Standard, up to ninety on Premium.
A `message_retention_days` above the tier's cap raises the tier (forced) rather than being
silently clamped by the platform.

**Auto-inflate only grows.** It raises throughput units up to the ceiling and never lowers
them; the bill follows the peak until someone reduces the reserved count by hand.

**Capture needs a path to storage.** The namespace's identity needs `Storage Blob Data
Contributor` on the container, and a firewalled storage account must let the namespace in - the
trusted-service path or a private endpoint. The first symptom of a missing path is an empty
container and an `ArchiveLogs` error.

**Geo-recovery copies metadata, not events.** After a failover the events that were in the
primary are gone. The pairing is an alias that a person or runbook fails over; clients connect
to the alias.

**Kafka clients and SAS.** With local auth off, a Kafka client authenticates with OAuth
(`SASL_OAUTHBEARER`) and the Event Hubs Data roles, not a connection string. A tool that only
takes a connection string cannot use the namespace.

**The modules disagree on what they expose.** The Terraform module has no input for the TLS
minimum, double encryption, zone redundancy, consumer groups or geo pairing; Bicep has all of
them. A decision the module cannot carry is named in the handover, never dropped.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <namespace id>` before a render.

## Not covered here, and why

Dedicated clusters, the schema registry, application groups (client throttling policy),
authorization rules and connection strings (no keys in a template), and the Kafka Connect
setup each carry decisions of their own and have no question set; a request for one is said
out loud, not improvised.
