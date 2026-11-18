# Infrastructure as Skills: Azure

A Claude Code plugin that authors Azure infrastructure as **Terraform or Bicep** from the
decisions each resource forces. Instead of generating code from a prompt, it interviews you
about the system - who uses it, what an outage costs, how much data loss is tolerable - and
writes an `infra-spec.yaml` that records every decision with where it came from. Code, tests,
an editable draw.io diagram and a decision document are rendered from that spec, onto
[Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/) first.

Parts of this plugin were developed with the help of AI (Claude Code). The plugin itself
works with an AI by design: it conducts the interview and renders the code, never applies
anything, and a person signs off the spec and the diagram before any code is written.

Defaults come from written security guardrails, not from the Azure portal or a module's
default, and are reported rather than asked. Each rendered resource ships with a test per
decision.

> [!TIP]
> **Use Sonnet or higher.** The plugin follows a multi-step protocol - interview, spec, diagram, sign-off, render - and its eval suite is measured on Sonnet. Haiku gets the spec decisions right less than half the time, skips the interview for a workload request and builds the application instead, and often does not load the plugin at all ([eval history](https://github.com/LemurDaniel/Infrastructure-as-Skills-Azure/blob/eval-history/README.md)).

> [!IMPORTANT]
> **The plugin's scripts need Python 3.9+ with PyYAML** (`pip install pyyaml`). They lay out
> and check the spec, draw the diagram and write the decision document. Without them the
> interview still runs, but the spec is unvalidated and no diagram is drawn.

> [!IMPORTANT]
> **This plugin requires [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases).** The architecture diagram is exported to `infra-diagram.drawio.png` with it (`winget install JGraph.Draw`, `brew install --cask drawio`). Without it you get the editable `.drawio` file only, no PNG, and the diagram review has nothing to look at.

> [!NOTE]
> **Terraform or Bicep is not required, but recommended.** The plugin writes the code without the CLI, but then it cannot run `fmt`, `validate`, `terraform test` or `bicep build` against it. The render is handed over marked as unverified.

## Skills

| Skill | What it does |
|---|---|
| `iac-authoring` | The entry point. Runs the interview and writes `infra-spec.yaml`. |
| `azure-resources` | Routes a named Azure resource to the question set that decides it. |
| `iac-diagram` | Draws the spec as an editable draw.io diagram for sign-off before any code. |
| `iac-rendering` | Renders the spec into Terraform or Bicep, with tests and a pipeline. |

## Patterns

A request that describes a whole system starts from a pattern: its parts, the few questions
only it asks, and the wiring between the parts - which identity holds which role, which
setting reads which secret. What you say still wins over what a pattern answers.

| Pattern | The system |
|---|---|
| `ai-chat-rag` | A chat application over your own documents: app, language model, search index, document storage |
| `private-webapp` | A web application with a relational database, connected without a password |
| `event-integration` | An API whose requests are processed in the background: gateway, functions, a queue or events |
| `container-microservices` | Several services as containers in one environment, an identity each, and their registry |

## Resources covered

70 resource types in ten families, each with a question set and rendering references for
both targets:

- **compute (12):** virtual machine, VM scale set, managed disk, availability set, maintenance
  configuration, AKS, App Service, function app, Container Apps, Container Instances, Static
  Web App, container registry
- **network (17):** virtual network, network security group, public IP, private endpoint,
  private and public DNS zone, route table, NAT gateway, Azure Firewall, load balancer, Bastion,
  VNet peering, Application Gateway with WAF, Front Door, Traffic Manager, DDoS protection
  plan, Network Watcher
- **data (8):** Azure SQL, SQL Managed Instance, PostgreSQL and MySQL flexible server, Azure
  Managed Redis, Cosmos DB, Data Factory, Purview
- **storage (4):** storage account, blob container, file share, queue
- **security (6):** Key Vault, Key Vault key and secret, user-assigned identity, role
  assignment, Defender for Cloud
- **messaging (6):** Service Bus, Event Hubs, Event Grid topic, namespace and system topic,
  Relay
- **integration (4):** API Management, Logic Apps, Automation account, Communication Services
- **ai (5):** AI Foundry, AI Search, AI Services, Machine Learning workspace, Bot Service
- **observability (6):** Log Analytics workspace, Application Insights, action group, alert
  rule, data collection rule, budget
- **recovery (2):** Backup vault, Recovery Services vault

A request for a resource without a question set is said out loud, never improvised.

## Install

```
/plugin marketplace add LemurDaniel/Infrastructure-as-Skills-Azure
/plugin install infrastructure-as-skills-azure
```

Then describe what you need, in your own words and language, for example: *"A storage
account for accounting, production, company network only. Terraform."*

## What the plugin runs, reads and writes

The plugin has no hooks and no MCP servers, and it sends nothing to any service of its own.
What happens in a session is done by Claude Code with your permission:

- **Local scripts.** Python 3 scripts bundled in the plugin validate a spec, a question set
  and a rendered pipeline, draw the diagram, and write the decision document. They need
  PyYAML and make no network calls.
- **Files in your repository.** A run writes `infra-spec.yaml`, `infra-decisions.md`, the
  diagram, the rendered Terraform or Bicep with its tests, and a pipeline or deploy script.
  It also keeps one marked section in your repository's `CLAUDE.md` current; only the text
  between its two markers is ever touched, and a section written by a newer plugin is left
  alone.
- **Tools on your machine.** Rendering runs `terraform` (`fmt`, `init`, `validate`, `test`) or
  `bicep` / `az bicep` (`build`, `lint`) when they are installed. These download providers
  and modules from `registry.terraform.io`, GitHub and `mcr.microsoft.com`. The
  diagram's PNG export uses the draw.io desktop app (without it the run stops at the editable
  `.drawio` file and says so), and the decision document converts
  to Word with `pandoc` if you ask for it.
- **Live version lookups.** AVM module versions are read from the module repositories' git
  tags, the Microsoft Container Registry tag list and the module READMEs, never recalled
  from memory.
- **Never applied.** The plugin does not run `terraform apply` or `az deployment ... create`.
  The pipelines it renders do that, in your CI, after your approval. Those pipelines sign in
  with the platform's short-lived OIDC token (for example `ARM_OIDC_TOKEN` in a GitLab job);
  the plugin itself never reads, stores or sends a credential.

The interview collects no personal data; the spec contains the decisions you state and the
values you give for names, regions and stages. Keep real secrets out of it: secret values are
left as placeholders to be filled outside the template.

## License

MIT, see the repository.
