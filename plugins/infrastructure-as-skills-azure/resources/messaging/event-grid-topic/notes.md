# Event Grid topic - what the question set cannot express

## Fixed at creation

- **The input schema.** A topic accepts one schema; changing it is a new topic and a cut-over of
  every publisher.
- **The data residency boundary.**
- **The name.** Regional, 3-50 characters, letters, digits and hyphens.
- **The region.**

## Ordering

Identity, the dead-letter storage account and container, the topic, the role assignments of
the delivery identity **on each target**, then the subscriptions (a subscription is validated
against its target when created, so the role and the target must exist first), then the
publishers and their publish role. The workspace before the diagnostic setting.

## Pitfalls

**A topic with no subscription drops every event.** The publish succeeds and nothing happens.
The first fault in a new deployment is a subscription whose target role was not yet effective.

**RBAC has propagation delay.** A role assigned to the delivery identity takes a minute or more
to take effect; a subscription created in the same apply can fail validation. The pattern
orders it and the render waits (`time_sleep` in Terraform).

**Webhooks must answer the validation handshake.** A subscription to a webhook sends a
validation event on creation; an endpoint that does not answer it makes the whole apply fail.
A webhook target is therefore an `open:` entry owned by its operator, and a protected endpoint
needs the Entra application settings on the subscription.

**Delivery with managed identity is the default for a reason.** A key-based destination puts a
secret in the subscription. The render uses `delivery_with_resource_identity` and
`dead_letter_with_resource_identity`; a target that cannot accept an identity (some webhooks) is
a named departure.

**Dead-lettered events are files nobody reads.** They are blobs in a container; alert on the
`DeadLetteredCount` metric and decide who reads and replays them.

**Private endpoints and delivery are separate.** A private endpoint on the topic closes the
*publish* path. The *delivery* path to a target behind a firewall depends on the target: a
trusted-service exception or the identity-based delivery path, not this topic's endpoint.

**Event Grid is at-least-once and unordered.** Receivers are idempotent and do not rely on
order; if they must, the answer is Service Bus, not a setting here.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <topic id>` before a render.

## Not covered here, and why

System topics (created per source resource), domains, namespaces with MQTT and pull delivery,
partner topics, advanced filters beyond the free-text filter, and the CloudEvents extension
attributes each carry decisions of their own and have no question set; a request for one is
said out loud, not improvised.
