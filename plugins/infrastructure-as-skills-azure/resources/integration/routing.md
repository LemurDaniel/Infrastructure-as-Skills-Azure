# Azure integration resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| API Management, APIM, API gateway, API management gateway, developer portal, rate limiting, API policy | `api-management/questions.yaml` | [notes](api-management/notes.md) |
| Application Gateway, WAF, web application firewall, layer-7 load balancer, ingress for a vnet | see the [network](../network/routing.md) family | Not here - it is a network resource |
| Front Door, CDN, global load balancer, edge | see the [network](../network/routing.md) family | Not here |
| Logic Apps, workflow, Power Automate | *not yet written* | - |
| Data Factory, Synapse pipelines | see the [data](../data/routing.md) family | Not here - `data-factory` lives with the data resources; Synapse has no set yet |
| Service Bus, Event Hubs, Event Grid | see the [messaging](../messaging/routing.md) family | Not here |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, `local_auth` and the requirements before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**"API gateway" in Azure is three different things.** API Management is the one that
authenticates, limits and routes *APIs* - policy, products, a developer portal. Application
Gateway is a layer-7 load balancer with a web application firewall in front of web
applications. Front Door is the global edge in front of both. A request that says "gateway" is
asked which of the three it means, with the one-line difference; the interview does not guess,
because they sit at different places in the network and are not substitutes.

**An integration resource is where the exposure decision becomes visible.** The gateway is the
one resource a consumer outside the system touches, so `network_exposure` lands here first. A
private deployment with a public API is `private_with_exceptions`, recorded as a departure on
this instance and nowhere else.

**The instance holds no secrets and the content is not the infrastructure.** API definitions,
policies per API and products change at the API team's pace. The set names them and wires the
identity and the network; it does not own their content.
