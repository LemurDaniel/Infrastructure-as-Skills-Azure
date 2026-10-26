# Event Grid namespace - what the question set cannot express

## Fixed at creation

- **Zone redundancy.** `isZoneRedundant` is written once; a different value is a new namespace.
  Left unwritten, the platform picks `true` in a region with zones.
- **The MQTT broker, once on.** `topicSpacesConfiguration.state` can go from `Disabled` to
  `Enabled` on an existing namespace but never back; a namespace that no longer needs the
  broker is replaced.
- **The name.** Regional, 3-50 characters, letters, digits and hyphens; it is the hostname of
  both the HTTP and the MQTT endpoint.
- **The region.** A routing topic must be in the same one.

## Ordering

Identity, the dead-letter storage account and container, the custom topic that MQTT messages
are routed to (and `EventGrid Data Sender` for the namespace's identity on it), the namespace,
then the namespace topics, then the role assignments of the namespace's identity **on each
push target**, then the subscriptions (a push subscription is validated against its target
when created), then the MQTT content in this order - CA certificates, topic spaces, client
groups, clients, permission bindings - then the publishers and receivers with their roles.
The workspace before the diagnostic setting.

Routing to a topic created in the same run is a **two-pass deployment**: the topic must exist
and the identity's role on it be effective before `routeTopicResourceId` is accepted. The
pattern orders it and the render waits (`time_sleep` in Terraform, a second stage in Bicep).

## Pitfalls

**Pull is the point.** A namespace topic with queue subscriptions gives a receiver behind a
firewall at-least-once delivery with no inbound path: it pulls a batch, then acknowledges,
releases or rejects each event. A workload that only needs push to a function is a custom
topic, not a namespace; a namespace is chosen for pull, for MQTT, or for both.

**The namespace has no key switch.** Every namespace topic carries two shared access keys the
service creates, and nothing in the API disables them. `local_auth: disabled` is therefore
recorded as `forced` and kept as a convention: no `listKeys`, no key in a setting, data-plane
access through `EventGrid Data Sender` / `EventGrid Data Receiver` on the topic. The audit
trail of who can list keys is the control-plane role assignment, so `EventGrid Contributor`
on the namespace is for the deploying principal only.

**No customer-managed key.** The type exposes no encryption property. The Terraform module
has a `customer_managed_key` input that the pinned version does not render into the resource
body; it is not written. `key_management: customer_managed` is recorded as not applicable on
this resource, not as done.

**The modules carry different halves of the namespace.** Terraform writes `sku` and
`capacity` but has no `isZoneRedundant`, no `minimumTlsVersionAllowed` and no
`topicSpacesConfiguration.state`; Bicep writes zone redundancy and the MQTT state but has no
`sku` or `capacity`. Each rendering reference names its gap and the escape hatch
(`azapi_update_resource` in Terraform; an authored `sku` block in Bicep); none of the four
decisions is dropped from the spec.

**MQTT clients are not Entra principals.** They authenticate with X.509 certificates against
a CA certificate or a thumbprint, and their permissions are bindings of client groups to topic
spaces. `role_assignments` does nothing for them. A device fleet is registered against the
namespace by its own provisioning process - the template holds the simulator and the gateway,
not ten thousand devices.

**A broker with no binding is silent.** Clients connect, publish and are refused on every
topic. The first MQTT fault is a topic space whose template does not cover the client's topic,
the second a client group whose query matches nobody.

**Throughput units do not grow by themselves.** There is no auto-inflate; a namespace short of
units throttles (HTTP 429, MQTT disconnects) until `capacity` is raised. Alert on the throttled
metric. One unit is 1 MB/s in and 2 MB/s out and 10,000 MQTT connections, so a fleet of
devices is sized by connections before bandwidth.

**Dead-lettered events are files nobody reads.** They are blobs in a container; alert on the
dead-lettered metric and decide who reads and replays them.

**Private endpoints and delivery are separate.** The endpoint closes the publish, pull and MQTT
paths. The push path to a target behind a firewall depends on the target: a trusted-service
exception or identity-based delivery, not this namespace's endpoint.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <namespace id>` before a render.
Eight categories exist; the `Successful*` ones are as large as the traffic.

## Not covered here, and why

Custom topics, system topics, domains and partner topics (separate resource types with sets
of their own), custom domains on the MQTT endpoint and their certificates, routing
enrichments, per-client certificate chains and attributes beyond the names listed, and the
`SecuredByPerimeter` network mode each carry decisions of their own and are either content or
have no question set; a request for one is said out loud, not improvised.
