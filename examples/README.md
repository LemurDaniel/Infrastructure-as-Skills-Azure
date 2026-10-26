# Examples

What good looks like, end to end: a request, the spec the interview wrote from it, and the
code rendered from the spec. Point at these rather than describing the shape — a
question-set author sees what a decision becomes, a renderer sees the file split and the
idiom, a reviewer sees what `source:` buys.

| Example | Targets | Scenario | Why it is here |
|---|---|---|---|
| [`chat-sandbox/`](chat-sandbox/) | Terraform | A small chat environment for development on one `[sandbox]` stage, public, deployed by hand: a containerised web app on App Service, models in AI Foundry, AI Search for retrieval, a storage account, a key vault holding the Entra app's client secret as a placeholder, its own Log Analytics workspace; `landing_zone: standalone`, no network | The first run of the whole flow with a customer in the conversation and both loops with subagents (`request.md` tells it). Authored Terraform (`module_source: authored`), the naming provider, `deploy.ps1` as the local delivery with the placeholder refusal; the three open items (image, models, the Entra app) as placeholders in the stage file. 118 decisions, 92 under `resources:` all asserted or marked (83 / 9), 32 test files. The run found the firewall trap (`public` + no network) and the sandbox cost rule, both written into the sets the same day; the diagram was finished by hand after the review |
| [`chatbot/`](chatbot/) | Terraform | An internal RAG chatbot on one stage (the request said "nur Produktion"): twelve kinds of resource, two of them twice - web app and MCP server on App Service, a connector function (Flex Consumption), a code interpreter on Container Apps, models in AI Foundry, AI Search, Cosmos DB, two storage accounts, Key Vault, Container Registry, Application Insights - in a spoke network of its own in a corp landing zone, the platform's DNS, its own workspace, every service private and keyless | The complex case, built from the sets added for it: 284 decisions across 20 resources, every role between them a `role_assignments` entry, `<set>__<instance>` keys for a second resource of one kind, seven open items (the Entra app registration among them). One root, 16 AVM module calls and the container environment authored - its module declares an ephemeral resource that mock providers cannot plan. 79 decisions are asserted, 205 marked not-testable with a reason. The Cosmos DB, Key Vault, Foundry, Search, Container Apps, Function App and Application Insights references were corrected by running it. No Bicep, no pipeline; nothing applied |
| [`chatbot-rag/`](chatbot-rag/) | Terraform | A small chat app on Azure AI Foundry with a RAG system on the default three-stage stack: standalone landing zone (own network, own private DNS zones, own workspace), private, `deploy_mechanism: github` | Authored resources throughout (`module_source: authored`), one `res.<kind>.tf` file per concern, a test file per resource and question group. Address ranges, models, runtime, subscriptions and groups are `open:` - the stage files hold placeholders until they are answered |
| [`orders-integration/`](orders-integration/) | Terraform (spec only) | An order platform on the default three stages in Germany West Central, **split over four resource groups** (main, network, data, observability - all created): Front Door Premium with WAF, an Application Gateway WAF_v2 and API Management (internal, Premium in production, Developer elsewhere) in front of a function app; Service Bus, Event Hubs with capture to a data lake and an Event Grid topic, all keyless; a Backup vault and a Recovery Services vault; one workspace, one key vault | The edge, messaging and recovery sets together. `private_with_exceptions`: every departure (public gateway origin, firewalled Service Bus Standard in development and test, the Event Grid service tag on the function app, subscription keys for the rate limit) is `overridden` with its reason, and the request's contradictions are written into `request.md`. 22 resource entries, 17 `open:` items, nothing assumed. Spec, decision document and diagram; no render, nothing applied |
| [`order-platform/`](order-platform/) | Terraform | An order platform on the default three stages in Germany West Central, **rendered as a customer repository**: `CLAUDE.md` and `.github/workflows/` at the root, everything else under `infra/`. `private_with_exceptions` with Front Door as the only public surface and an Application Gateway, API Management, a function app and a virtual machine behind it; Service Bus, Event Hubs and an Event Grid system topic; two storage accounts; a Backup vault and a Recovery Services vault; its own network, DNS zones and workspace (`landing_zone: standalone`), `deploy_mechanism: github` | A full render as a customer repository, with the family split of `chatbot/` (seven modules: app, data, messaging, network, observability, recovery, security, each with its own test file, plus a wiring test) and the pipeline. 23 resource entries, 6 `open:` items rendered as `OPEN-` placeholders in the stage files, 63 decisions all covered by `check_render_coverage.py`, `check_spec.py` and `check_pipeline.py` clean. `request.md` holds the request verbatim (English, unlike `orders-integration/`). The Terraform tests and `validate` were not run when it was added; nothing applied |


## What each directory holds

```
<case>/
  request.md            # the user's words, verbatim
  deploy.ps1            # the local delivery for deploy_mechanism: local - no pipeline
  CLAUDE.md             # what the render leaves in the customer's repository: the spec is the
                        # source of truth, a code change is a spec change first (rule 11)
  request.pipeline.md   # a follow-up request, where an extension run added to the spec
  infra-spec.yaml       # the interview's output - the artefact everything else follows from
  infra-decisions.md    # the spec as the customer reads it, rendered by export_decisions.py
  naming.yaml           # the convention, a full copy of naming.default.yaml - Terraform only
  environments/*.tfvars # one file per resolved stage (Terraform); bicep/main.<stage>.bicepparam (Bicep)
  *.tf, *.tfvars        # the Terraform render, one concern per file
  tests/*.tftest.hcl    # plan-only, platform mocked, naming provider real - one
                        # assert per spec decision, checked by check_render_coverage.py
  .github/workflows/    # the pipeline for deploy_mechanism: github, one stage block per
                        # stage; inert here (GitHub reads only the repository root),
                        # checked by check_pipeline.py
  # an open stage's environments/<stage>.tfvars holds placeholders (00000000-..., OPEN-...)
```

## Running one

```powershell
cd examples/chatbot-rag
terraform init -backend=false   # the root holds an empty backend "azurerm" {}; the pipeline passes
                                # -backend-config="key=<workload>/<stage>.tfstate" and the rest
terraform fmt -check -recursive
terraform validate      # terraform plan -var-file=environments/production.tfvars needs credentials
terraform test
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_render_coverage.py ./infra-spec.yaml
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/export_decisions.py ./infra-spec.yaml --language de
```

`chatbot/` is split into family modules: `terraform init -backend=false && terraform test` in
`modules/ai`, then in the root for the wiring test.

Needs the `azurerm`, `azapi`, `modtm`, `random` and `LemurDaniel/naming` providers from the
registry. No credentials: the tests mock `azurerm`, `azapi` and `modtm`, and nothing plans
against a subscription. The lock file is not committed, so `init` resolves the current
provider versions - if a render stops validating after a release, that is a finding for the
rendering reference, not for the example.

## Rules

- An example is **rendered, never applied**. Subscription ids and names are placeholders.
- An example is regenerated from its spec when a rendering reference changes, and the diff
  is the review. Hand-editing the `.tf` without touching the reference is how the two drift.
- `request.md` is the eval prompt verbatim where the example comes from a case; the spec
  must satisfy that case's graders.
