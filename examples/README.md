# Examples

What good looks like, end to end: a request, the spec the interview wrote from it, and the
code rendered from the spec. Point at these rather than describing the shape — a
question-set author sees what a decision becomes, a renderer sees the file split and the
idiom, a reviewer sees what `source:` buys.

| Example | Targets | Scenario | Why it is here |
|---|---|---|---|
| [`chatbot/`](chatbot/) | Terraform | An internal RAG chatbot on one stage (the request said "nur Produktion"): twelve kinds of resource, two of them twice - web app and MCP server on App Service, a connector function (Flex Consumption), a code interpreter on Container Apps, models in AI Foundry, AI Search, Cosmos DB, two storage accounts, Key Vault, Container Registry, Application Insights - in a spoke network of its own in a corp landing zone, the platform's DNS, its own workspace, every service private and keyless | The complex case, built from the sets added for it: 284 decisions across 20 resources, every role between them a `role_assignments` entry, `<set>__<instance>` keys for a second resource of one kind, seven open items (the Entra app registration among them). One root, 16 AVM module calls and the container environment authored - its module declares an ephemeral resource that mock providers cannot plan. 79 decisions are asserted, 205 marked not-testable with a reason. The Cosmos DB, Key Vault, Foundry, Search, Container Apps, Function App and Application Insights references were corrected by running it. No Bicep, no pipeline; nothing applied |
| [`chatbot-rag/`](chatbot-rag/) | Terraform | A small chat app on Azure AI Foundry with a RAG system on the default three-stage stack: standalone landing zone (own network, own private DNS zones, own workspace), private, `deploy_mechanism: github` | Authored resources throughout (`module_source: authored`), one `res.<kind>.tf` file per concern, a test file per resource and question group. Address ranges, models, runtime, subscriptions and groups are `open:` - the stage files hold placeholders until they are answered |


## What each directory holds

```
<case>/
  request.md            # the user's words, verbatim
  request.pipeline.md   # a follow-up request, where an extension run added to the spec
  infra-spec.yaml       # the interview's output - the artefact everything else follows from
  infra-decisions.md    # the spec as the customer reads it, rendered by export_decisions.py
  naming.yaml           # the convention, a full copy of naming.default.yaml - Terraform only
  environments/*.tfvars # one file per resolved stage (Terraform); bicep/main.<stage>.bicepparam (Bicep)
  platform.yaml         # the platform profile the platform team would have written
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
