# Progress

The handoff between sessions. Read it at the start of one, rewrite it at the end of one —
the goal rarely changes, the rest does. Keep it tight: what is here is what the next
session starts from, and what is not here it re-derives. The direction behind the next
thing is `ROADMAP.md`.

## Goal

A Claude Code plugin that authors Azure infrastructure as Terraform or Bicep from an
interview, consistently: the same request produces the same decisions, every decision is
recorded with where it came from, and a backend renders from that record — onto Azure
Verified Modules first, authored resources second.

## Decisions, and why

- **Question sets, not modules or templates.** The hard part of a resource is its
  decisions, not its syntax. Generic generation gets the syntax right and the decisions
  wrong.
- **Spec in the middle.** `infra-spec.yaml` is the handover; code is rendered from it. It
  makes two backends comparable and regeneration a diff.
- **AVM first, authored second.** A resource with an `Available` Azure Verified Module
  renders as a call to it, every decision an explicit input; a type without one renders
  authored and the spec says so (`implementation: authored`, `source: forced`). The modules
  already implement what the first authored render got wrong — the diagnostic setting
  that collects no blob logs, the endpoint named after the index — with one interface in
  both targets. `deployment.module_source` records it once; `module_telemetry` beside it,
  because the modules phone home by default and a reviewer will ask. **Asked first, in both
  modes** (owner's call, 2026-10-24, reversing "not asked"): a `customer` question in plain words, before
  the description, `avm` recommended, `authored` recommended when the repository holds authored blocks;
  skipped when the user stated it or a carried spec has it. Evals not re-run on it. The contract is
  `core/iac-rendering/references/avm.md`; each resource reference opens with the decision
  → module input table and the call, and keeps the authored rendering below it.
- **Module coordinates and versions stay in the renderer, never in the spec.** Versions
  are `0.y.z` and move monthly; they are looked up live (MCR tag list, module repo git
  tags) and pinned in the code. The tables in the references are dated snapshots.
- **One triggering skill, families as routing, question sets as knowledge.** The skill
  listing has a shared character budget and drops descriptions silently when it overflows.
  A skill per family overflowed at the sixth family.
- **Defaults from the guardrails, not the portal — and not the module.** AVM defaults
  diverge from the guardrails too (`Standard_GRS`, 365 days retention, infrastructure
  encryption off, public access on), so every decision is written on the call even where
  it matches.
- **Landing-zone model.** A workload lands in an application landing zone; the platform
  (hub, DNS zones, central workspace) exists and is referenced, never built.
- **Authored rendering references target `azurerm` 5.x.** `public_network_access` is a
  string there; the 4.x bool is deprecated and `validate` does not warn. The AVM Log
  Analytics module still pins `azurerm` 4.x, and the AzAPI-based AVM modules (storage,
  vnet) need `azapi`, `modtm`, `random` — the root's provider set is the union.
- **Plan-only tests mock the platform.** A referenced vnet or workspace is a `data` block,
  which a plan reads from Azure; `mock_provider "azurerm"` with parseable ids keeps the
  test credential-free. With a module in the middle, `azapi` and `modtm` are mocked the
  same way and the assert target is the module's `resource` output — settled 2026-10-18
  on the storage module v0.10.0: the account body, identity, name and parent id are
  observable at plan time, the `private_endpoints` output gives name and a null zone
  group id; what the module builds in child modules (blob service, diagnostics, role
  assignments, the endpoint body) is not, and is marked not-testable — 9 of 24 storage
  decisions. The `resource` output is sensitive, so a failing assert prints
  `(sensitive value)`; the error message carries the expected value.
- **Sub-resource names go through `<?SUBNAME>`**, not appended to a finished name. The
  first cross-backend diff found the Terraform render naming a private endpoint
  `…-01-blob` while Bicep said `…-blob-01`; the convention has the token for exactly this.
- **Tests are part of the render, with coverage as the contract - both targets.** One
  assert per spec decision, named by its key path; a decision the target cannot observe
  is marked with its reason. Terraform asserts on the plan (`terraform test`); Bicep
  asserts on the compiled ARM (`tests/*.armtest.yaml`, `run_arm_tests.py`, 2026-10-18):
  a module call is a nested deployment whose parameter values are the decisions, a loop
  a `copy` whose expression text is matched by regex, symbolic resource names forced by
  `bicepconfig.json`. `check_render_coverage.py` checks spec against tests per target,
  so "everything is tested" is a gate, not an intention.
- **The interview is the customer's, alone.** Decided 2026-10-18: the person answering
  sits in front of the plugin without an engineer, so every question carries an
  `audience`, the customer answers about six requirement questions in their own words,
  technical decisions are derived from those (`source: requirement`), platform facts come
  from a `platform.yaml` (`source: platform`), and an engineer question nobody can answer
  becomes an `open:` entry instead of a question. Customer mode is the default; the
  engineer mode is entered on request or when the repository shows it. The plugin is
  public and has to hold for any use case. Beside the diagram, a decision document in the
  customer's language (Markdown first, Word offered once) is a deliverable. Plan:
  `ROADMAP.md`, phases A–E. B1 and B3 landed the same day: every one of the 82
  questions carries an `audience` (customer 13, engineer 49, platform 20) and
  `check_question_set.py` fails without one; `platform.yaml` is the engineer's profile
  (`references/platform.md`, a commented template beside it, `--platform` to check one),
  read at precedence 3 as `source: platform`, never written by an interview.
- **Requirements live in the deployment set, the map on the resource.** B2 and B4,
  2026-10-18. The three customer questions (`outage_impact`, `data_loss_tolerance`,
  `data_access_pattern`) are a `requirements` group in `deployment.yaml` rather than
  the separate `requirements.yaml` the roadmap named: one resolution mechanism, no
  second scope. A resource question derives through its own `derived_from: { question,
  map }`, so a new resource maps an existing requirement without touching the
  deployment set; the spec records `source: requirement` + `derived_from`, and the
  default answer derives the guardrail default so an unanswered requirement changes
  nothing. Both checks verify the map covers every answer. Customer questions in a
  run: environment, exposure, mandates, the three requirements, and log retention when
  the deployment owns the workspace - six, the budget (the module choice, asked first, is one more). `iac-authoring` now has the two
  modes: customer (default; only `customer` questions asked, the rest resolved or
  opened) and engineer.
- **The decision document is rendered, not written.** B5, 2026-10-18. Every question
  carries `plain` (`en` and `de`, `{value}` where the value goes) and, where a raw value
  means nothing to a customer, `plain_values`; `export_decisions.py` turns a spec into
  `infra-decisions.md` in the customer's language - what follows from their answers with
  the derived decisions under each, what the rules set, departures, open items, an
  appendix with every key. Both examples carry theirs. Word is a `pandoc` conversion
  offered once in Phase 5, never a second source.
- **The stack is the default, and per-stage values are never literals.** Owner's call,
  2026-10-18: one code base goes through `development`, `test`, `production` unless the
  customer says otherwise ("nur prod", "Sandbox"); a request naming one stage names that
  stage of the stack. `context.environments` replaces `context.environment`; every value
  is one for all stages or a map keyed by stage, a stage nobody could answer for is an
  `open:` entry naming it, and a stage with open values gets no parameter file. A
  question with `per_environment: true` (ranges, prefixes, subscription, group,
  referenced platform parts) renders as a parameter with its value in
  `environments/<stage>.tfvars` / `main.<stage>.bicepparam`, one state per stage by
  backend key, never a workspace. Stages are separated by subscription by default
  (`stage_isolation`), resource groups being the lesser form. Parity between stages is
  the rule; `non_production_savings` (default enabled) lets `non_production_default`
  relax cost knobs - replication LRS, retention 30 - outside production, and the check
  refuses the field on anything security-shaped. Both examples re-rendered: the first
  with `environments/production.tfvars` and a development-stage test run, the second
  with `main.staging.bicepparam` and per-stage ARM assertions; the other stages are open.
- **`naming.yaml` is copied for Terraform only.** Owner's call, 2026-10-18: the provider
  reads it at plan time, nothing in a Bicep deployment does. A Bicep root gets its name
  vars generated from the plugin's convention and a `naming.yaml` only for a stated
  `custom` departure, holding the departures alone.
- **No registry alias, no registry modules — for the owner's own registry.** `br/public:`
  needs no alias and is the default; `br/modules:` is only rendered when
  `bicepconfig.json` already has it (`implementation: reuse`).

## Open

- **Todo: an AVM version drift check.** The versions in `avm.md` and the six resource
  references are dated snapshots. A scheduled check that compares them against the MCR
  tag lists and the module repos' git tags and reports only what moved - never edits -
  would keep the tables honest. Checkable goal, read-only gate, the dated table as its
  memory; not set up yet (the owner's call, 2026-10-17).
- `patterns/` is empty; composition is specified on paper only. AVM pattern modules
  (`private-link-private-dns-zones`, `hub-networking`) are candidates for what a pattern
  skill wraps rather than re-implements.
- No render has been applied: neither `terraform plan` nor `what-if` has run against a
  subscription, so the renders are validated, not proven.
- **The eval baseline exists** (`evals/baseline.json`, full run of 2026-10-18, $5.44):
  `greenfield-telemetry` and `private-storage-on-platform` 3/3 on every grader,
  `vague-public-dev` 78% - two runs split the exposure by stage and none opened the
  empty role assignments. Both are plugin gaps and both rules were written after that
  run (posture is one per system, `check_spec.py` now refuses a stage split on a
  non-stage question; an empty role list with shared keys off is an `open:` entry).
  The next full run should lift the vague case; accept it with `--update-baseline`
  after reading it. Four plugin rules came out of the three eval rounds in total: a
  default is not an assumption, a referenced hub forces the landing zone, a parameter
  is never open, a stated value holds in every stage. No grader checks
  `implementation` or `module_source` yet; B6's customer-question graders are not
  written.
- **`compute/app-service` landed 2026-10-18** (28 questions, both checks green): plan and
  web app as two AVM modules per target (Terraform `avm-res-web-serverfarm` v2.0.8 +
  `avm-res-web-site` v0.24.1, both AzAPI; Bicep `web/serverfarm` 0.7.0 + `web/site`
  0.24.0). No new customer question: zone redundancy and instance count derive from
  `outage_impact`, exposure, basic auth and diagnostics are inherited. Not yet done: no
  rendered example, no tests exercised (the Terraform plan module exposes only `name` and
  `resource_id`, so its three decisions will be `not-testable`; the `siteConfig` property
  paths for the asserts are to be read off a first `terraform test` run), the diagnostic
  category names are from memory and want `az monitor diagnostic-settings categories
  list` against a real site, and `time` provider is required by the site module. The
  `integration_subnet` under `network_ownership: create` is specified as forced by the
  virtual-network set, which has no delegation question yet.
- **The pipeline landed as references, 2026-10-18** (not yet as renders): the `delivery`
  group in `deployment.yaml` (`deploy_mechanism` customer/required, `pipeline_auth`
  platform/workload_identity, `pipeline_approvals` engineer/production) and
  `core/iac-rendering/references/pipelines{,.github,.ado,.gitlab,.local}.md`, derived from
  the owner's scaffolds (`ARCHIVE__ProgrammingResources/Scaffoldings`; action versions
  there were stale and are re-looked-up). GitLab has no scaffold behind it and is marked
  untested. `scripts/check_pipeline.py` checks the invariants of `pipelines.md` per
  platform; `tests/run_pipeline_tests.py` (55 cases) runs it on five fixtures taken from
  the references (GitHub x2 targets, Azure DevOps, GitLab, local) and on ~45 single-invariant
  breaks. **A rendered example exists** (2026-10-18): `examples/private-storage-on-platform`
  got `request.pipeline.md` (an extension run), `deploy_mechanism: github` in its spec and
  `.github/workflows/` with all three stage blocks; development and test are `open:` and
  hold **placeholder** stage files (all-zero GUID, `OPEN-<what>`) - the owner's call
  2026-10-18, reversing "an open stage gets no file": the scaffold stands, and invariant 11
  of `pipelines.md` (the plan job's first step refuses a placeholder; the stage chain then
  holds every later stage, production included) keeps it from deploying. Run on it: `check_pipeline.py`, `check_spec.py`, `actionlint` 1.7.12
  (on a copy in a throwaway git repo; it resolves the reusable workflow from the repository
  root), and the pipeline's own validate steps (`fmt`, `init -backend=false`, `validate`,
  `test`, 7 passed). Not run: anything that needs Azure or a GitHub repository - the
  environments, the federated login, `plan`, `apply`; `init -backend-config=...` was run
  against a dummy account and got as far as authentication, so the arguments are valid.
  **Found by doing it:** `terraform init -backend-config=...` without a backend block is
  ignored without an error (local state, gone with the runner) - the example now holds an
  empty `backend "azurerm" {}`, `terraform-idiom.md` and `pipelines.md` say so, and
  `check_pipeline.py` fails on a root without one. **The other two examples landed the same
  day:** `greenfield-telemetry` (Bicep) got `deploy_mechanism: azure_devops` - `azure-pipelines.yml`,
  `.azure-pipelines/stage.yml`, working directory `bicep/`, placeholder `bicepparam` files for
  its three open stages - and `private-storage-gitlab` is the storage example's Terraform
  root with a `.gitlab-ci.yml` (one spec names one system, so GitLab needs its own). Run:
  `check_pipeline.py` on both, `bicep build`/`build-params`/`lint` on all four stages,
  `run_arm_tests.py` and `check_render_coverage.py`, `terraform test` on the GitLab copy,
  and the two guard steps extracted from the YAML and executed per stage (open stages exit
  1, the resolved one 0). **Found by doing it:** a resolved stage's file must not spell a
  marker out even in a comment - the grep reads comments, and staging's header comment
  would have refused staging itself; `check_pipeline.py` caught it. Not run: Azure DevOps
  or GitLab accepting their file (no lint available offline), and GitHub with Bicep has a
  fixture and `actionlint` but no rendered example. `spec.md` documents the keys; the
  diagram does not draw the pipeline, by the owner's call (not needed). Not yet done: no
  eval case for the delivery questions, and `deploy_mechanism` is a customer question on top
  of an interview already over its six-question budget.
- **`security` landed 2026-10-23** (`key-vault` 23 questions, `user-assigned-identity` 5; both checks green):
  taken from the adessoGPT architecture diagram (`adessoGPT-architektur.drawio.png`), a
  complex case that needs ~10 more resource sets. Owner's call: all Azure resources, family
  by family, one commit each; the Entra app registration is **not** a resource set - an
  `open:` entry owned by the identity team. Versions looked up 2026-10-23: Key Vault TF
  0.12.0 (**Orphaned**, `azurerm`-based, `< 5.0`) / Bicep 0.14.2, identity TF 0.5.3
  (`azurerm`, `< 5.0`) / Bicep 0.6.0. **Found by doing it:** module defaults diverge from the
  guardrails again (SKU `premium` in both, `enableVaultForDeployment` true in Bicep, public
  access true in TF). Owner's addition: `secret_placeholders` - a dummy secret filled in
  later; **neither module protects the real value from the next deployment**, so the render
  creates placeholders outside the module (TF `ignore_changes = [value]`; Bicep only when
  the secret does not exist). Not done: no rendered example, no tests, the diagram has no
  icons for the two, the diagnostic category names are from memory, and the `keys` member
  names of both modules are to be read from the README at render time.
  `check_repo_consistency.py` crashes on Windows (cp1252 decoding of the `claude plugin
  validate` output) unless run with `PYTHONUTF8=1`.
- **`data/cosmos-db` landed 2026-10-23** (31 questions, API for NoSQL only; AVM TF 0.11.0,
  `azurerm ~> 4.0`, / Bicep 0.21.1). Derived: zone redundancy from `outage_impact`, backup
  from `data_loss_tolerance` (30 days is the longest tier, `three_months` leaves a stated
  gap). **Found by doing it:** the Terraform module has no input for Cosmos DB's own data-plane
  roles (rendered next to it with `azurerm_cosmosdb_sql_role_assignment`); the two modules
  disagree on consistency and backup-redundancy defaults. The partition key is an `open:`
  entry when nobody answers. Not done: no example, no tests, the throughput of a container is
  one value for all of them, and the diagnostic category names are from memory.
- **`ai` landed 2026-10-23** (`foundry` 26 questions, `search-service` 20; both checks green;
  AVM TF cognitiveservices 0.11.1 AzAPI but `azurerm < 5.0`, search 0.3.0 `azurerm ~> 4.0` /
  Bicep 0.19.1 and 0.13.0). **Found by doing it:** neither Foundry module creates a project
  (rendered beside the module as `accounts/projects`); the modules disagree on local auth,
  outbound restriction, replica count. **A judgement to review:** `deployment_sku` defaults to
  `DataZoneStandard` - the portal's default `GlobalStandard` processes prompts in any region;
  the owner may want it the other way. The model list is `open:` when nobody answers and is
  regional (quota, versions) - looked up at render time, never recalled. Not done: no example,
  no tests, the diagnostic category names (`Audit`, `RequestResponse`, `AzureOpenAIRequestUsage`,
  `OperationLogs`) are from memory, the project API version is a placeholder.
- **`compute` extended 2026-10-23** (`container-registry` 22, `container-apps` 24, `function-app`
  29 questions; both checks green). Registry: TF 0.8.0 (`azurerm < 5.0`) / Bicep 0.13.1; Container
  Apps: env TF 0.5.1 (`azurerm ~> 4.0`, many deprecated inputs) + app TF 0.9.0 (AzAPI) / Bicep
  0.16.0 + 0.23.0; Function App reuses `web-site` (TF 0.24.1 / Bicep 0.24.0) with `kind` function.
  **Found by doing it:** Bicep's Container App module defaults to external ingress, HTTP allowed,
  port 80 (Terraform the opposite); the registry modules disagree on retention, bypass and export;
  Container Apps and Function Apps default to a **user-assigned identity**, unlike App Service,
  because the first revision/start needs its roles before the app exists; the environment logs
  through a diagnostic setting, not the workspace's shared key. Not done: no examples, no tests;
  the Function App's per-plan subnet delegation (`Microsoft.App/environments` for Flex,
  `Microsoft.Web/serverFarms` for Premium) is from memory and to be confirmed; Container Apps
  session pools (the "code interpreter" of the adessoGPT diagram) have no set; the `app-service`
  boundary "no function apps / Container Apps" is now stale.
- **`application-insights` (12) and `network-security-group` (9) landed 2026-10-23**, which
  completes the resource sets of the adessoGPT diagram (AVM TF 0.5.0 / 0.6.0, both AzAPI only;
  Bicep 0.8.0 / 0.5.4). Not done: no examples, no tests. **Found by doing it:** the modules
  disagree on IP masking (Bicep stores client IPs by default) and retention; a closed component
  needs the platform's Azure Monitor Private Link Scope (`open:` entry without one); the NSG's
  baseline rules per `subnet_purpose` (`notes.md`) are from general knowledge and are confirmed
  against each service's documentation before a render; the NSG is associated through the
  virtual-network set (`subnets_expecting_nsg` records it, `subnet_delegations` carries the
  delegation the three compute sets point at).
- **The chatbot example landed 2026-10-23** (`examples/chatbot/`, the generic form of the
  adessoGPT diagram; Terraform only, one stage): request, spec (20 resources, 284 decisions,
  seven `open:` entries), a root of 16 AVM module calls, tests (7 files, **79 decisions asserted,
  205 marked not-testable with a reason**, `terraform test` 7 passed, coverage 284/284), decision
  document (de), diagram. Nothing applied; no Bicep, no pipeline. The spec was written with a
  scaffold (`build_spec.py`, resolves the sets against the request) that is not shipped. **What
  running it corrected in the sets:** Cosmos DB's Terraform module has a different diagnostic
  interface (`log_categories`, metrics `Requests`/`SLI`); `store_client_ip` is not inverse of
  `disable_ip_masking`; the naming kind variant is `Microsoft.Web/sites::function`. **What it
  found in the tooling:** the spec had no way to say a second resource of one kind - now
  `<set>__<instance>` (`spec.md`, `check_spec.py`, `export_decisions.py`, which also drops the
  stage prefix when there is one stage); `avm-res-app-managedenvironment` cannot be planned under
  mock providers (an ephemeral resource in every version), so the environment is authored and the
  departure is in the spec's `_target_overrides`; Key Vault, Container Registry and the Container
  App module expose no attribute at all; a list output compared to a list literal is false in
  HCL (compare `jsonencode`). **The diagram script** now reads instance keys, draws identities
  and NSGs in a zone of their own, takes subnet delegations from the spec, routes callers on
  tracks of their own (colour per caller from three callers up), keeps the PaaS services in one
  row and the actor lines off the resource group's border; `run_diagram_tests.py` has the chatbot
  as a case. Still open: no icon for Foundry and Container Apps in draw.io's library (nearest
  used); PaaS-to-PaaS lines are not routed (said in `wiring.purposes`); the Entra app
  registration, the shared private link from search to storage and the model quota are `open:`.
- **The chatbot example was regrouped 2026-10-23 into one submodule per family** (owner's call:
  the flat root of 16 AVM calls was hard to read). `granularity: per-family` is in `spec.md` and
  `terraform-idiom.md` (Grouped AVM calls): the root is `modules.<family>.tf` calls only,
  `modules/<family>/` holds `avm.<resource>.tf`, `private_endpoints.tf`, `roles.tf`, variables,
  outputs and `versions.tf`. **The tests moved with it**: `modules/<family>/tests/<family>.tftest.hcl`
  (identity, observability, network, security, ai, data, compute: 7 files, all pass, run with
  `terraform -chdir=modules/<family> test`) plus `tests/wiring.tftest.hcl` for the root;
  `check_render_coverage.py` reads both, 284/284. **Found by doing it:** a module-level `depends_on`
  defers the module's `data` lookups to apply, so names are unknown at plan (the wait is now an input,
  `role_scope_ids`, on the `time_sleep`); a whole-module output is sensitive and infects the root;
  `mock_provider "azapi"` needs the provider declared in the family's `versions.tf`; the naming
  provider is configured in each test file with the root's seed. Not done: Bicep has no equivalent
  yet (`bicep-idiom.md` unchanged), and the generator for the layout is the Python scratch of this
  session - the idiom is the contract, the example the proof.
- **Rendering with agents, drafted 2026-10-24** (`iac-rendering/references/agents.md`, step 11 of the
  skill): two arms from one spec, code (code agent, pipeline agent, read-only test agent, 3 passes) and
  diagram (diagram agent, read-only review agent that looks at the PNG, 2 passes), findings with a
  severity and one cause (`render` goes back to the agent, `spec` is the main agent's and restarts both
  arms), `polish` never goes back. **Trialled once** on a copy of the chatbot spec (`deploy_mechanism:
  github` added): diagram arm ran 2 passes, code and pipeline were rendered, coverage 284/284,
  `check_pipeline.py` green after the spec fix. From a short path `init` and `validate` passed and
  `terraform test` ran 44 of 45 (a type error in one Foundry assert, `"false"` against `false`); in a
  long scratch path `init` fails on the Windows path limit and `subst` does not help (git resolves
  it), so a render has to sit at a short path before `init`. **What it found:** a review of the picture finds what the
  geometry check does not (claims the spec does not carry); the generator drew "no public access" over a
  public workspace, read `public_network_access` from one group only, counted a Container Apps
  environment as a private endpoint and gave the first caller the endpoint blue - fixed in
  `new_diagram.py`, asserted in `run_diagram_tests.py`. **Open:** `agents.md` lacks a severity *not
  checkable* (a reviewer counted an unverifiable number as an error) and one-cause-per-finding; the
  chatbot spec says `granularity: single` while the example is per-family; an `open:` entry for a value
  that sits in a stage file needs `environments:` or `check_pipeline.py` takes the stage as resolved;
  `terraform.md` tables are stale in places (`log_categories` for the Key Vault, Search, Foundry, ACR,
  Cosmos DB and NSG modules). The trial's render was **discarded** (owner's call, 2026-10-24) and is not
  in the repo; what it left is the list above.
- **Next:** the same case rendered to Bicep from the one spec (the cross-backend diff is what
  tests the sets), a deploy pipeline once the owner names the system, and `patterns/` - the
  wiring in this example (roles between resources, the private link, the order identity -> vault
  -> consumer) is what a pattern would own. Then `ROADMAP.md` C1's `data` (Azure SQL, PostgreSQL)
  and `integration` (Service Bus).
- **A sandbox subscription for real plans, applies and the deploy agent** (`ROADMAP.md`
  A5, E): the owner sets it up — subscription, federated credential for OIDC, a fenced
  resource group. Not available yet (2026-10-18).
- The customer interview (`ROADMAP.md` B), still open: the evals graders (B6) - a
  grader that counts the questions put to the customer and one that fails on Azure
  vocabulary in them. The decision document's `open:` lines stay English, because the
  spec's `open:` questions are English; a run translates them in the conversation.
- The stack's stage files are written only for resolved stages; nothing yet generates
  the other stages' files once their `open:` entries are answered - that is an extension
  run, and the first one has not been exercised.
- **The diagram's PNG is repaired and checked on export** (2026-10-20, taken from the
  owner's profile skill `drawio-diagrams`). The draw.io CLI writes a bad zTXt CRC and no
  IEND with `--embed-diagram`; both example PNGs had it. `iac-diagram/scripts/` now has
  `drawio_png.py` (check/labels/extract/embed/repair/icons), `verify_diagram.py` (diagram
  against spec, umlauts for `de`) and `tests/run_png_tests.py`. Not exercised: a fresh
  export through `export_diagram.py` end to end, and the customer-edit diff path in
  `SKILL.md` (extract, regenerate, diff). Not taken over: the repo-card style library.
  The diagram has no subscription frame (owner's call, 2026-10-20: it changes per
  environment and only adds a layer); the resource group is the outermost container.
  One file is delivered, `infra-diagram.drawio.png`: the export deletes the `.drawio` it
  came from (`--keep` leaves it), and the examples carry only the PNG.
- **What the plugin adds over plain Claude has been measured once, as a pilot** (2026-10-23,
  `evals/outcome/outcome-private-storage`, 1 run per arm, ~$5): same request, no mention of a
  spec, scored on the union of `infra/**/*.tf` and `*.tfvars` by
  `.claude/skills/plugin-evals/scripts/score_outcome.py` (the harness reads one file per
  grader, real code is many). Plugin 17/17, without 15/17: the difference is AVM (hand-written
  `azurerm_storage_account`) and tests (none); every security decision was equal in both arms.
  So the case that was easy for the model shows little; the claim to test is the many small
  decisions (replication, soft delete, infrastructure encryption, SFTP). Needs 3 runs and
  harder cases before it counts. The spec-graded cases (`evals/spec/`) cannot be run without
  the plugin - the spec is its format. No Linux in WSL here, so `terraform validate` in an
  eval needs a Linux runner.
- **Evals sit in groups** (`spec/`, `diagram/`, `interview/`, `outcome/`); a case reaches the
  plugin with `plugins: ["../../.."]`. The 0-cost load check prints "0 case(s)" with or
  without the move and proves nothing - the first paid run is the check that the runner
  still finds them.
- **Terraform tests are always several files**, one per question-set group
  (`terraform-idiom.md`, Tests): the two examples were split and pass `terraform test` and
  the coverage check. The Bicep side (`*.armtest.yaml`) is still one file per example.
- A cloud session needs `registry.terraform.io`, `releases.hashicorp.com`, `github.com`
  release downloads and `mcr.microsoft.com` allowed, and installs `terraform` and `bicep`
  into `~/.local/bin` itself (neither is in the image). Done once on 2026-10-18.

## Next

Add the two missing rules to `agents.md` (a severity *not checkable*, one cause per finding). Widen the plugin-vs-plain measurement (3 runs per arm, cases on the small decisions, ~$15-25)
before trusting the pilot. Re-run the eval suite (full, ~$5) against the two rules written after the baseline and
accept the run if `vague-public-dev` rises without the other two dropping. Then
the chatbot case in Bicep (Open, above); the sets from 2026-10-23 are now rendered once, in
Terraform, and have no Bicep render and no eval case. B6's two graders and the
extension run that writes a further stage's file once its open entries are answered stay
on the list; A5 waits on the owner's sandbox.
