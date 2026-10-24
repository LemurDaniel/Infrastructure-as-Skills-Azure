---
name: azure-resources
description: Routes a request that names an Azure resource to the question set that decides it, for Terraform or Bicep. Storage (storage account, blob, ADLS Gen2, data lake, file share, queue), network (vnet, subnet, address space, private endpoint), observability (Log Analytics workspace, log retention, diagnostics), compute (App Service, web app, App Service plan, function app, Container Apps, container registry), security (Key Vault, secrets, managed identity), data (Cosmos DB, NoSQL), ai (AI Foundry, Azure OpenAI, AI Search). AVM (Azure Verified Modules) first. Use whenever one of these is created, changed, reviewed or ported between targets.
---

# Azure resources

The routing unit behind [iac-authoring](../iac-authoring/SKILL.md), which is the entry
point for any Azure infrastructure request and runs the interview. This skill does one
thing: find the family, then the question set — for a request that names a resource
directly, and for every resource the interview reaches. It does not interview and it does
not render — those are iac-authoring and [iac-rendering](../iac-rendering/SKILL.md).

It exists as its own skill for a budget reason worth knowing before editing it. Every
skill's description sits in a shared listing budget, and a description that overflows it
is dropped silently — the skill stays installed and stops matching. A skill per family
would have spent that budget by the sixth family. One description for all of them costs a
fifth as much, and it is kept separate from iac-authoring so that the resource list
growing here never crowds out the entry description — the workload and target terms a
request actually carries.

## Families

| Family | Covers | Routing |
|---|---|---|
| storage | storage accounts; containers, shares and queues planned | [resources/storage/routing.md](../../resources/storage/routing.md) |
| network | virtual networks and subnets; network security groups; peering, route tables planned | [resources/network/routing.md](../../resources/network/routing.md) |
| observability | Log Analytics workspaces; Application Insights; alerts planned | [resources/observability/routing.md](../../resources/observability/routing.md) |
| compute | App Service (plan and web app); function apps; Container Apps; Container Registry | [resources/compute/routing.md](../../resources/compute/routing.md) |
| security | Key Vault; user-assigned managed identity | [resources/security/routing.md](../../resources/security/routing.md) |
| data | Cosmos DB (API for NoSQL); SQL, PostgreSQL planned | [resources/data/routing.md](../../resources/data/routing.md) |
| ai | AI Foundry / Azure OpenAI with model deployments; AI Search | [resources/ai/routing.md](../../resources/ai/routing.md) |

Read the family's `routing.md`. It names the question set for the request, or says plainly
that none exists yet.

**A request for a family that is not in this table is said out loud.** SQL,
Container Apps, Service Bus — none have a family yet. Generating one from the guardrails
while this table implies coverage removes the one property that makes this plugin worth
using, and does it silently. Say that no question set backs it, offer to generate from
[the guardrails](../iac-authoring/references/guardrails.md) with that recorded in the spec,
and let the user decide.

## Order of work

1. **[iac-authoring](../iac-authoring/SKILL.md) first, always.** The
   [deployment set](../iac-authoring/questions/deployment.yaml) — context, posture, network
   and workspace ownership, mandates — is resolved before any resource question, and its
   answers decide which resource questions survive. Starting with the resource set asks
   things the deployment set would have answered.
2. The family's question set, through the interview protocol.
3. [iac-rendering](../iac-rendering/SKILL.md), from the spec, never from the conversation.

A request naming several resources across families — "ein Storage Account im eigenen VNet
mit Log Analytics" — is one interview and one spec, not three. The deployment set is asked
once and every family's questions inherit from it.

## Adding a family

1. `resources/<family>/routing.md`, and one `<resource>/` directory per resource holding
   `questions.yaml`, `notes.md`, `terraform.md` and `bicep.md` — copy an existing family
2. A row in the table above
3. The family's terms in this skill's `description` — the terms people actually type, not
   the Azure resource provider names

**Never a new skill.** Measure this description against the per-entry cap of 1,536
characters before adding terms; past roughly 1,200, prune the least-typed ones rather than
splitting — a split is the per-family layout this replaced.
