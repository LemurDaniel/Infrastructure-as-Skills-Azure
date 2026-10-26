# Event Grid system topic - what the question set cannot express

## Fixed at creation

- **The source and the topic type.** A system topic belongs to one source resource; a
  different source or type is a new topic.
- **The region.** It is the source's region, or `global` for the `Microsoft.Resources.*` types
  (subscriptions, resource groups). A topic in the wrong region is refused at creation.
- **The name.** Regional, 3-128 characters, letters, digits and hyphens.
- **One topic per source and type.** A second system topic of the same type on the same
  source fails. A shared source - the subscription, a platform resource group, a hub storage
  account - may already have one; the render checks before creating, and a pattern that
  needs the subscription's events reuses the existing topic and adds a subscription to it.

## Ordering

The source resource, the identity (the topic's own is created with it), the dead-letter
storage account and container, the topic, then the role assignments of the topic's identity
**on each target and on the dead-letter container**, then the subscriptions (a subscription
is validated against its target when created, so the role and the target must exist first),
then the handlers. The workspace before the diagnostic setting.

## Pitfalls

**A system topic is not a custom topic.** Nobody publishes to it; the source does. There is no
input schema, no key, no `EventGrid Data Sender`, no network surface - the only decisions are
which source, how to deliver, and where failures go. A request for "an Event Grid topic the
application publishes to" is the `event-grid-topic` set.

**The topic type is case-sensitive and not guessable from the reference.** `Microsoft.KeyVault.vaults`
and `Microsoft.Storage.StorageAccounts` differ in casing for no reason anyone remembers;
the list in the question set is the common part, `az eventgrid topic-type list` the authority.
A type outside the list is a departure from the enum, not a refusal.

**Some sources need something switched on first.** A storage account emits blob events only
on a v2 or Data Lake account; a subscription or resource-group topic sees only control-plane
operations; a key vault emits certificate, key and secret lifecycle events with no setting.
The source's set owns the switch; this set only subscribes.

**RBAC has propagation delay.** A role assigned to the topic's identity takes a minute or more
to take effect; a subscription created in the same apply can fail validation. The pattern
orders it and the render waits (`time_sleep` in Terraform, a second deployment in Bicep).

**The Bicep module can grant the identity's roles on the targets.** `externalResourceRoleAssignments`
exists on it for exactly this. It is not used: the role on a target belongs to the pattern that
owns the wiring, in the same place for both targets, not inside one target's module call.

**Webhooks must answer the validation handshake.** A subscription to a webhook sends a
validation event on creation; an endpoint that does not answer it makes the whole apply fail.
A webhook target is therefore an `open:` entry owned by its operator, and a protected endpoint
needs the Entra application settings on the subscription.

**Storage events are many.** A bulk upload emits an event per blob; a subscription without an
event-type filter on a busy account delivers every tier change and policy run too. The
subject prefix (`/blobServices/default/containers/<name>/`) is the second filter and lives in
the subscription entry.

**Do not dead-letter into the source.** A storage-account topic whose dead-letter container
is in the same account emits a `BlobCreated` for every dead-lettered event. The dead-letter
account is another one.

**Event Grid is at-least-once and unordered.** Handlers are idempotent and do not rely on
order; if they must, a Service Bus queue with sessions sits in between.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <topic id>` before a render. The
type has one category, `DeliveryFailures`.

## Not covered here, and why

Custom topics, namespaces (pull delivery, MQTT), domains and partner topics are separate
resource types with sets of their own. Advanced filters beyond event types and subject
prefix, delivery attribute mappings (custom headers on delivery), batching on function and
webhook targets, and the source-side switches (which account kind emits which events) each
carry decisions of their own and are content of the subscription entry or of the source's
set; a request for one is said out loud, not improvised.
