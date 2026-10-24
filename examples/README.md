# Examples

What good looks like, end to end: a request, the spec the interview wrote from it, and the
code rendered from the spec. Point at these rather than describing the shape — a
question-set author sees what a decision becomes, a renderer sees the file split and the
idiom, a reviewer sees what `source:` buys.

| Example | Targets | Scenario | Why it is here |
|---|---|---|---|
| [`private-storage-on-platform/`](private-storage-on-platform/) | Terraform, Bicep | One storage account on the default stack (development, test, production - the request named production), behind a referenced hub and workspace, BSI C5 | The straightforward case: every platform part is referenced, one resource, `granularity: single`. Rendered to both targets from the one spec on the **Azure Verified Modules** (`avm-res-storage-storageaccount` v0.10.0, `avm/res/storage/storage-account` 0.33.1, resolved 2026-10-18), so the two can be diffed. The git history before that date holds the authored render of the same spec. A second request (`request.pipeline.md`, an extension run) added `deploy_mechanism: github` and the **GitHub Actions pipeline** - all three stage blocks, with placeholder stage files for development and test, which are still `open:`; the pipeline refuses to deploy a placeholder |
| [`greenfield-telemetry/`](greenfield-telemetry/) | Bicep | Three resources on a four-stage stack (the request named staging), nothing referenced: own network with two subnets, own workspace, private storage, `landing_zone: standalone`; only staging's stage file is resolved | The `create` branches the first example never reaches, including the privatelink zone the deployment owns and links. Four AVM modules in one root, the wiring between them in the root. The first render with tests against the compiled ARM, and the first spec carrying `source: requirement`. A second request (`request.pipeline.md`) added `deploy_mechanism: azure_devops` and the **Azure DevOps pipeline** (`azure-pipelines.yml`, `.azure-pipelines/stage.yml`): four stage blocks with the Bicep root `bicep/` as working directory, and placeholder parameter files for the three open stages |
| [`private-storage-gitlab/`](private-storage-gitlab/) | Terraform | The storage example's Terraform root with a **GitLab CI pipeline** instead of GitHub Actions (`request.pipeline.md`: "Der Code liegt in GitLab") | One spec names one system, and two pipelines on one state race for its lock, so the GitLab render needs a spec of its own. Same code as `private-storage-on-platform/`, no Bicep and no diagram; only `.gitlab-ci.yml`, the spec's `deploy_mechanism` and the decision document differ. The GitLab file is written from the documentation alone and has not run against a project |

| [`chat-sandbox/`](chat-sandbox/) | Terraform | A small chat environment for development on one `[sandbox]` stage, public, deployed by hand: a containerised web app on App Service, models in AI Foundry, AI Search for retrieval, a storage account, a key vault holding the Entra app's client secret as a placeholder, its own Log Analytics workspace; `landing_zone: standalone`, no network | The first run of the whole flow with a customer in the conversation and both loops with subagents (`request.md` tells it). Authored Terraform (`module_source: authored`), the naming provider, `deploy.ps1` as the local delivery with the placeholder refusal; the three open items (image, models, the Entra app) as placeholders in the stage file. 118 decisions, 92 under `resources:` all asserted or marked (83 / 9), 32 test files. The run found the firewall trap (`public` + no network) and the sandbox cost rule, both written into the sets the same day; the diagram was finished by hand after the review |
| [`chatbot/`](chatbot/) | Terraform | An internal RAG chatbot on one stage (the request said "nur Produktion"): twelve kinds of resource, two of them twice - web app and MCP server on App Service, a connector function (Flex Consumption), a code interpreter on Container Apps, models in AI Foundry, AI Search, Cosmos DB, two storage accounts, Key Vault, Container Registry, Application Insights - in a spoke network of its own in a corp landing zone, the platform's DNS, its own workspace, every service private and keyless | The complex case, built from the sets added for it: 284 decisions across 20 resources, every role between them a `role_assignments` entry, `<set>__<instance>` keys for a second resource of one kind, seven open items (the Entra app registration among them). One root, 16 AVM module calls and the container environment authored - its module declares an ephemeral resource that mock providers cannot plan. 79 decisions are asserted, 205 marked not-testable with a reason. The Cosmos DB, Key Vault, Foundry, Search, Container Apps, Function App and Application Insights references were corrected by running it. No Bicep, no pipeline; nothing applied |

## What each directory holds

```
<case>/
  request.md            # the user's words, verbatim
  deploy.ps1            # the local delivery for deploy_mechanism: local - no pipeline
  request.pipeline.md   # a follow-up request, where an extension run added to the spec
  infra-spec.yaml       # the interview's output - the artefact everything else follows from
  infra-decisions.md    # the spec as the customer reads it, rendered by export_decisions.py
  naming.yaml           # the convention, a full copy of naming.default.yaml - Terraform only
  environments/*.tfvars # one file per resolved stage (Terraform); bicep/main.<stage>.bicepparam (Bicep)
  platform.yaml         # the platform profile the platform team would have written
  *.tf, *.tfvars        # the Terraform render, one concern per file
  tests/*.tftest.hcl    # plan-only, platform mocked, naming provider real - one
                        # assert per spec decision, checked by check_render_coverage.py
  tests/*.armtest.yaml  # the Bicep tests: one entry per decision against the compiled
                        # ARM, run by run_arm_tests.py, counted by the same coverage check
  .github/workflows/    # the pipeline for deploy_mechanism: github, one stage block per
                        # stage; inert here (GitHub reads only the repository root),
                        # checked by check_pipeline.py
  # an open stage's environments/<stage>.tfvars holds placeholders (00000000-..., OPEN-...)
  bicep/main.bicep      # the Bicep render of the same spec
  bicep/main.bicepparam # its parameters - the same values as terraform.tfvars
  bicep/bicepconfig.json # symbolicNameCodegen on, so the tests can address resources by name
```

## Running one

```powershell
cd examples/private-storage-on-platform
terraform init -backend=false   # the root holds an empty backend "azurerm" {}; the pipeline passes
                                # -backend-config="key=invoicing/production.tfstate" and the rest
terraform fmt -check -recursive
terraform validate      # terraform plan -var-file=environments/production.tfvars needs credentials
terraform test
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_render_coverage.py ./infra-spec.yaml
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_pipeline.py ./infra-spec.yaml
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/export_decisions.py ./infra-spec.yaml --language de

bicep build --stdout bicep/main.bicep > $null
bicep build-params bicep/main.staging.bicepparam --stdout > $null   # one per resolved stage
bicep lint bicep/main.bicep

cd ../private-storage-gitlab
terraform init -backend=false && terraform validate && terraform test
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_pipeline.py ./infra-spec.yaml

cd ../greenfield-telemetry
bicep build --stdout bicep/main.bicep > $null && bicep lint bicep/main.bicep
bicep build-params bicep/main.staging.bicepparam --stdout > $null   # one per stage, placeholders included
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_pipeline.py ./infra-spec.yaml
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/run_arm_tests.py ./infra-spec.yaml
python3 ../../plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_render_coverage.py ./infra-spec.yaml
```

Needs the AVM module and the `azurerm`, `azapi`, `modtm`, `random` and
`LemurDaniel/naming` providers from the registry, and the Bicep CLI, which resolves the
module from `mcr.microsoft.com`. No credentials: the tests mock `azurerm`, `azapi` and
`modtm`, and nothing plans or what-ifs against a subscription. The lock file is not
committed, so `init` resolves the current `~> 0.10.0` / `~> 5.0` / `~> 2.11` / `~> 1.0` —
if a render stops validating after a release, that is a finding for the rendering
reference, not for the example.

## The cross-backend diff

The spec design promises that one spec rendered twice differs only where the platforms
genuinely differ. `private-storage-on-platform` is the measurement, taken twice: on the
authored render (2026-10-17) and again on the AVM render (2026-10-18). Every decision in
the spec lands in both renders with the same value; what differs:

| | Terraform | Bicep | Verdict |
|---|---|---|---|
| Private endpoint name | `pep-we-prod-invoicing-blob-01` via the provider's `subname` parameter | same, assembled from vars | **Was a divergence** in the authored render: Terraform appended `-blob` after the index. Fixed in `terraform.md` |
| `network_rules` / `networkAcls` with public access off | present, `Deny` + `AzureServices` — the module renders it into the body either way | present | **Was a divergence** (omitted on the Terraform side); the module removed it, and the bypass became testable |
| Role assignments | `role_definition_id_or_name` by name | `roleDefinitionIdOrName` by name, union-typed `role` param | **Was a divergence** (a GUID map on the Bicep side); the module's shared interface removed it |
| Diagnostics | `diagnostic_settings_storage_account` + `diagnostic_settings_blob` inputs | `diagnosticSettings` + `blobServices.diagnosticSettings` params | Same: the module knows the account emits metrics only |
| Soft delete, versioning | `blob_properties` input, nested objects | `blobServices` param, flat `…Enabled` / `…Days` pairs | Same decision, different shape — documented in each reference |
| Per-endpoint output | map keyed by sub-resource from the module's `private_endpoints` output | the module's `privateEndpoints` array | Shape of each module's output |
| Naming inputs | the provider reads `naming.yaml` at plan time | `locationCodes` holds only the regions the deployment uses | Inherent: a new region is a regenerated var block, see `naming.md` |
| Provider-level | `storage_use_azuread = true`; `azapi`, `modtm`, `random` declared for the module | — | Inherent: no provider in Bicep; `az` authenticates with Entra ID anyway |
| Subscription, resource group | `var.subscription_id` on both providers; the group read by `data` and passed as `parent_id` | the deployment's scope on the command line | Inherent |
| Telemetry | `enable_telemetry = true` | `enableTelemetry: true` | Same, written on both calls |

Two of the three genuine divergences the authored render had were the module's doing:
the modules implement the same interface on both sides, which is the argument for AVM
first, measured.

## Rules

- An example is **rendered, never applied**. Subscription ids and names are placeholders.
- An example is regenerated from its spec when a rendering reference changes, and the diff
  is the review. Hand-editing the `.tf` or `.bicep` without touching the reference is how
  the two drift.
- `request.md` is the eval prompt verbatim where the example comes from a case; the spec
  must satisfy that case's graders.
- A new divergence between the two renders of one spec is a finding for a rendering
  reference, never something to patch in one example.
