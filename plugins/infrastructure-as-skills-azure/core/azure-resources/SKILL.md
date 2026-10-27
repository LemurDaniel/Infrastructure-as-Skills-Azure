---
name: azure-resources
description: Routes an Azure resource to its question set (Terraform or Bicep). Storage (storage account, blob, file share), network (vnet, private endpoint, private DNS, DNS zone, public IP, peering, route table, NAT, firewall, load balancer, Bastion, Application Gateway, Front Door, Traffic Manager, DDoS, Network Watcher), observability (Log Analytics, action group, alert, DCR), compute (VM, scale set, disk, AKS, App Service, slot, function app, Container Apps, ACI, Static Web App, registry), security (Key Vault, managed identity, RBAC, Defender), data (Cosmos DB, SQL, SQL MI, PostgreSQL, MySQL, Redis, Data Factory, Purview), ai (Foundry, AI Search, Speech, Document Intelligence, ML workspace, Bot), messaging (Service Bus, Event Hubs, Event Grid, MQTT, Relay), integration (API Management, Logic Apps, Communication Services), backup (Backup vault, Recovery Services). AVM first. Use when one is created, changed, reviewed or ported.
---

# Azure resources

**Load [iac-authoring](../iac-authoring/SKILL.md) first** if this run has not loaded it: it is
the entry point and holds the rules every run keeps (the version gate, the interview, no code
before the sign-off). This skill alone never writes a spec or code.

The routing unit behind [iac-authoring](../iac-authoring/SKILL.md), which is the entry
point for any Azure infrastructure request and runs the interview. This skill does one
thing: find the family, then the question set — for a request that names a resource
directly, and for every resource the interview reaches. It does not interview and it does
not render — those are iac-authoring and [iac-rendering](../iac-rendering/SKILL.md).

New resource terms go into this skill's description, never into the one of iac-authoring:
all descriptions share one listing budget, and an overflow silently stops a skill matching.

## Families

| Family | Covers | Routing |
|---|---|---|
| storage | storage accounts; blob containers, file shares, queues | [resources/storage/routing.md](../../resources/storage/routing.md) |
| network | virtual networks and subnets; network security groups; Application Gateway with WAF; Front Door; peering; route tables; NAT gateway; Azure Firewall; load balancer; Bastion; public IP; private endpoint; private DNS zone; public DNS zone; Traffic Manager; DDoS protection plan; Network Watcher and flow logs | [resources/network/routing.md](../../resources/network/routing.md) |
| observability | Log Analytics workspaces; Application Insights; action groups; alert rules (metric, log query, activity log); data collection rules and endpoints | [resources/observability/routing.md](../../resources/observability/routing.md) |
| compute | App Service (plan, web app and deployment slots); function apps; Container Apps; Container Registry; virtual machines, scale sets, managed disks, availability sets; AKS; Static Web Apps; Container Instances | [resources/compute/routing.md](../../resources/compute/routing.md) |
| security | Key Vault, keys, secrets; user-assigned managed identity; role assignments; Defender for Cloud | [resources/security/routing.md](../../resources/security/routing.md) |
| messaging | Service Bus; Event Hubs; Event Grid custom topics, namespaces (MQTT, pull delivery) and system topics; Azure Relay | [resources/messaging/routing.md](../../resources/messaging/routing.md) |
| integration | API Management (the API gateway); Logic Apps (Standard and Consumption); Communication Services | [resources/integration/routing.md](../../resources/integration/routing.md) |
| recovery | Backup vault; Recovery Services vault | [resources/recovery/routing.md](../../resources/recovery/routing.md) |
| data | Cosmos DB (API for NoSQL); Azure SQL; SQL Managed Instance; PostgreSQL and MySQL flexible server; Managed Redis; Data Factory; Purview | [resources/data/routing.md](../../resources/data/routing.md) |
| ai | AI Foundry / Azure OpenAI with model deployments; AI Search; single-service AI accounts (Speech, Vision, Language, Document Intelligence); Machine Learning workspace; Azure Bot | [resources/ai/routing.md](../../resources/ai/routing.md) |

Read the family's `routing.md`. It names the question set for the request, or says plainly
that none exists yet.

**A request for a family that is not in this table is said out loud.** Synapse, Databricks,
Data Explorer, Fabric, policy, management groups, budgets — none have a set yet. Generating one from the guardrails
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

A request naming several resources across families — "a storage account in its own VNet
with Log Analytics" ("ein Storage Account im eigenen VNet mit Log Analytics") — is one interview and one spec, not three. The deployment set is asked
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
