# Infrastructure as Skills: Azure

A Claude Code plugin that authors Azure infrastructure as **Terraform or Bicep** from the
decisions each resource forces. Instead of generating code from a prompt, it interviews you
about the system - who uses it, what an outage costs, how much data loss is tolerable - and
writes an `infra-spec.yaml` that records every decision with where it came from. Code, tests,
an editable draw.io diagram and a decision document are rendered from that spec, onto
[Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/) first.

Defaults come from written security guardrails, not from the Azure portal or a module's
default, and are reported rather than asked. Each rendered resource ships with a test per
decision.

## Skills

| Skill | What it does |
|---|---|
| `iac-authoring` | The entry point. Runs the interview and writes `infra-spec.yaml`. |
| `azure-resources` | Routes a named Azure resource to the question set that decides it. |
| `iac-diagram` | Draws the spec as an editable draw.io diagram for sign-off before any code. |
| `iac-rendering` | Renders the spec into Terraform or Bicep, with tests and a pipeline. |

## Resources covered

49 resource types in ten families, each with a question set and rendering references for
both targets:

- **compute:** virtual machine, VM scale set, managed disk, availability set, AKS, App Service,
  function app, Container Apps, Container Instances, Static Web App, container registry
- **network:** virtual network, network security group, public IP, private endpoint, private
  DNS zone, route table, NAT gateway, Azure Firewall, load balancer, Bastion, VNet peering,
  Application Gateway with WAF, Front Door
- **data:** Azure SQL, PostgreSQL and MySQL flexible server, Azure Managed Redis, Cosmos DB
- **storage:** storage account, blob container, file share, queue
- **security:** Key Vault, Key Vault key and secret, user-assigned identity, role assignment,
  Defender for Cloud
- **messaging:** Service Bus, Event Hubs, Event Grid topic
- **integration:** API Management
- **ai:** AI Foundry, AI Search
- **observability:** Log Analytics workspace, Application Insights
- **recovery:** Backup vault, Recovery Services vault

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
  and modules from `registry.terraform.io`, GitHub and `mcr.microsoft.com`. The optional
  diagram export uses the draw.io desktop app if present, and the decision document converts
  to Word with `pandoc` if you ask for it.
- **Live version lookups.** AVM module versions are read from the module repositories' git
  tags, the Microsoft Container Registry tag list and the module READMEs, never recalled
  from memory.
- **Never applied.** The plugin does not run `terraform apply` or `az deployment ... create`.
  The pipelines it renders do that, in your CI, after your approval.

The interview collects no personal data; the spec contains the decisions you state and the
values you give for names, regions and stages. Keep real secrets out of it: secret values are
left as placeholders to be filled outside the template.

## License

MIT, see the repository.
