# Storage queue - what the question set cannot express

## Fixed at creation

- **The name.** 3-63 characters, lowercase letters, digits and single hyphens, unique within the
  account. Renaming is a new queue and a cut-over.
- **The account**, which is the parent: a queue cannot move.

## Ordering

The account first, then the queue, then its role assignments, then the producer and the worker.
With the account module the queue is part of the account's call and the order is internal.

## Pitfalls

**A storage queue is not Service Bus.** No ordering, no duplicate detection, no dead-letter
queue, no topics, a 64 KB message limit and a maximum time-to-live of seven days by default
(configurable up to infinite per message). A message that is received and not deleted becomes
visible again after the visibility timeout and its `DequeueCount` rises; setting a failing
message aside after N tries is the **consumer's** code. A requirement for any of these is
Service Bus (`needs_dead_letter_or_ordering`).

**With shared keys off the data plane is Entra-only.** A client library or a Functions queue
trigger configured with a connection string cannot reach the queue; it needs the identity-based
trigger settings and a data role. The first symptom is a trigger that never fires.

**A closed account is closed to the queue too.** Data-plane access follows the account's
network rules and private endpoints. The private endpoint for queues is its own sub-resource
(`queue`) of the account, and its DNS zone is `privatelink.queue.core.windows.net`: a
`private_endpoint_subresources` list that omits `queue` leaves the queue unreachable from the
network.

**Poison messages and a growing queue are invisible by default.** There is no built-in alert
on queue length. The `QueueMessageCount` metric of the queue service is the one to watch, set
up by the monitoring owner.

## Not covered here, and why

Message TTL tuning, access policies, SAS, and the consumer's retry and poison-message handling
each carry decisions of their own and have no question set; a request for one is said out loud,
not improvised.
