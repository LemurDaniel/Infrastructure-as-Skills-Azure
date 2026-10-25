# Azure messaging resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| Service Bus, queue, topic, subscription, message broker, dead letter, enterprise messaging | `service-bus/questions.yaml` | [notes](service-bus/notes.md) |
| Event Hubs, event hub, Kafka endpoint, telemetry stream, event streaming, capture | `event-hubs/questions.yaml` | [notes](event-hubs/notes.md) |
| Event Grid, event grid topic, event routing, webhook delivery, system topic | `event-grid-topic/questions.yaml` | [notes](event-grid-topic/notes.md) - custom topics only |
| Event Grid namespace, MQTT broker, pull delivery | *not yet written* | A separate resource type with clients, topic spaces and permission bindings |
| Event Grid system topic, Event Grid domain | *not yet written* | System topics are created per source resource and belong to it; a domain is a multi-tenant topic collection |
| Azure Queue Storage, storage queue | see the [storage](../storage/routing.md) family | Not here - a queue inside a storage account |
| Notification Hubs, SignalR, Web PubSub | *not yet written* | - |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, `local_auth`, `key_management` and the requirements before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**Which one is a question about the message, not about the product.** A command that must be
handled exactly once by one worker, with retries and a dead-letter queue, is Service Bus. A
firehose of telemetry that many readers replay at their own pace is Event Hubs. A notification
that something happened, routed to whoever subscribed, is Event Grid. A request that says
"messaging" without more asks which of the three - the interview does not guess, because the
three have different delivery guarantees, not different prices.

**Messaging resources are the glue other resources point at.** A Function App trigger, a
Container Apps scale rule, an Event Grid subscription and a Log Analytics export each name a
namespace or topic that has to exist first. The role a consumer needs on it is granted in the
pattern that wires them, never here.

**No key in a template, ever.** With `local_auth: disabled` the namespaces have no connection
strings; consumers use Entra ID and a data-plane role. A consumer that cannot is a named
departure and an `open:` entry.

**Private connectivity is a tier decision here.** Service Bus needs Premium for a private
endpoint, Event Hubs needs Standard or above, Event Grid topics support them on every tier.
The sets say which, and force the tier from the exposure answer.
