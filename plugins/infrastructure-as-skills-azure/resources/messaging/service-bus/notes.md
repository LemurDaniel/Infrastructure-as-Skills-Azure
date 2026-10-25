# Service Bus - what the question set cannot express

## Fixed at creation

- **The tier, in practice.** Premium cannot be lowered to Standard, and moving a Standard
  namespace to Premium is a migration into a new namespace (`migrationConfiguration` in
  Bicep), not an edit. The private-endpoint requirement is what makes the choice early.
- **Partitions** of a Premium namespace.
- **Sessions and duplicate detection** of a queue, topic or subscription: `requires_session`
  and `requires_duplicate_detection` cannot be flipped on an existing entity. A queue whose
  receivers later need ordering is a new queue and a cut-over.
- **The name.** Global, 6-50 characters, letters, digits and hyphens, must start with a letter
  and not end with `-sb` or `-mgmt`. A name from the convention can still collide.
- **The region.**

## Ordering

Identity, key vault and key (customer-managed key only), the namespace, then queues and topics,
then the role assignments (a data-plane role on an entity needs the entity), then the
consumers. The workspace before the diagnostic setting. A geo pairing needs both namespaces
and the entities of the secondary **empty**: it is the last step, not part of the first
apply.

## Pitfalls

**A private namespace is a Premium namespace.** There is no private endpoint on Basic or
Standard. A deployment with `network_exposure: private` that asks for "the cheap tier" gets
Premium, recorded as forced; the cost is a messaging unit running around the clock. If that is
not acceptable, the answer is a public namespace with a firewall, which is a recorded
departure and needs Premium for the firewall too - so below Premium the namespace is open
to the internet.

**The modules disagree on defaults.** Local authentication is on in Terraform and off in
Bicep, trusted services bypass off in Terraform and on in Bicep, and both modules default to
Premium and double encryption. Every decision is written on the call.

**Messages in flight are not replicated.** Zone redundancy keeps them across datacenters;
geo-disaster recovery copies only the **metadata** (entities, rules). After a regional
failover the messages that were in the primary are gone, and the senders must be able to
resend. A `critical` outage answer that assumes otherwise is wrong.

**Geo-recovery is an alias, not two active namespaces.** The pairing exposes one alias name
that points at the primary until a failover is *initiated by a person or a runbook*; there is
no automatic failover. The clients must connect to the alias, not the namespace. Failover
breaks the pairing.

**A dead-letter queue is storage nobody empties.** It counts against the entity's size, so a
poison message that is never handled eventually fills the entity and the senders fail. Alert
on the dead-letter count (a metric) and decide who reads it.

**Lock duration vs. processing time.** A handler slower than the lock duration processes the
message twice. Long work renews the lock; raising the lock to the 5-minute maximum only moves
the problem.

**SAS is off, so connection strings do not work.** A client library or a tool that takes a
connection string needs Entra ID configuration instead (`DefaultAzureCredential`, the
fully-qualified namespace). Functions and Container Apps scale rules need the
identity-based setting, not a `ServiceBusConnection` string.

**Role names are the data-plane roles.** `Azure Service Bus Data Sender`, `...Data Receiver`,
`...Data Owner`; `Contributor` on the namespace manages it and reads no messages.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <namespace id>` before a render.
`RuntimeAuditLogs` and `ApplicationMetricsLogs` exist only on Premium.

## Not covered here, and why

Authorization rules and connection strings (no keys in a template), SQL filter rules on
subscriptions, forwarding chains between entities, auto-forward and scheduled enqueue
policy, JMS/AMQP specifics, and the Service Bus Relay each carry decisions of their own
and have no question set; a request for one is said out loud, not improvised.
