# Progress

The handoff between sessions. Read it at the start of one, rewrite it at the end of one —
the goal rarely changes, the rest does. Keep it tight: what is here is what the next
session starts from, and what is not here it re-derives. The git history holds how things
got here; this file holds what holds now. There is no roadmap: the direction is `ideas/`,
one file per idea, and the one next thing is at the end of this file.

## Goal

A Claude Code plugin that authors Azure infrastructure as Terraform or Bicep from an
interview, consistently: the same request produces the same decisions, every decision is
recorded with where it came from, and a backend renders from that record — onto Azure
Verified Modules first, authored resources second.

## Decisions, and why

The rules the plugin is built on, each with the reason. The skills and references carry
the detail; this list says what was decided and why, so a session does not reopen it.

- **Question sets, not modules or templates.** The hard part of a resource is its
  decisions, not its syntax. Generic generation gets the syntax right and the decisions
  wrong.
- **Spec in the middle.** `infra-spec.yaml` is the handover; code is rendered from it. It
  makes two backends comparable and regeneration a diff. The spec names decisions, never
  a backend's attribute spelling; module coordinates and versions stay in the renderer
  (`0.y.z`, looked up live, pinned in the code; the tables in the references are dated
  snapshots).
- **AVM first, authored second.** A resource with an `Available` module renders as a call
  to it, every decision an explicit input; a type without one renders authored and the
  spec says so (`implementation: authored`, `source: forced`). The modules already
  implement what the first authored render got wrong, with one interface in both targets.
  `deployment.module_source` records it once, `module_telemetry` beside it (default
  `disabled` for new specs). The module choice is a `customer` question, asked in Phase 0
  (owner's call, 2026-10-24), skipped when the repository or a carried spec answers it.
- **Phase 4 opens with the design as a tick list** (2026-10-24): before the defaults
  account and before any file, one line per part in the customer's words, the connections,
  what costs money; one question "Passt das Design?" and the spec is written only when the
  list is right. A missing part is cheaper to find here than after the picture.
- **Every question set is read before Phase 3 asks** (2026-10-24): the resources the
  request names plus those a deployment decision forces in (private exposure → vnet,
  diagnostics → workspace). A set read later has `customer` questions that could not be
  asked. The first install test of the eval agent read `virtual-network` and
  `log-analytics-workspace` only after Phase 5 began; its spec shows no question lost
  (the deployment set had asked them), so the rule is a guard, not a fix for a seen loss.
  Whether `user-assigned-identity` was read at all in that run is unchecked.
- **`network_requirements` is a customer requirement** (2026-10-24): may the network be
  chosen freely, or are address ranges assigned or a connection to the company network
  (hub, VPN) given; it pre-answers `landing_zone` and through it the network's ownership
  and exposure, and opens the addressing for the network team when ranges are assigned.
  No option in the customer batch is marked recommended: the default is a fallback, not
  advice - except the address range when the network is free, which is offered as three
  sizes out of 10.100.0.0 with the one that fits the system recommended (sizing the plugin
  derives, not a guess about the organisation); the endpoint prefix is cut from it. The first install test's customer said
  "Netz egal, kein VPN" and the interview had no question for it. The batch rule says the
  host's four-questions-per-call limit means several calls in a row, never a batch cut to
  four.
- **`context.language` names the customer's language** (2026-10-24): `en` or `de`, set by
  Phase 0 from the language the request is written in, never asked. The picture, the
  decision document and the customer-facing spec text follow it; the scripts read it and
  `--language` only overrides. Before, the language was guessed at drawing time.
- **The target is Phase 0's first question** (2026-10-24): Terraform or Bicep before the
  module choice and the naming mechanism, two options, none recommended; Phase 1 only
  reads the layout and asks nothing.
- **`iac-authoring` is the entry, `azure-resources` carries the resource names, families
  route, question sets are knowledge** (entry moved 2026-10-24). The skill listing has a
  shared character budget and drops descriptions silently when it overflows; a skill per
  family overflowed at the sixth family. The entry moved because the first install test
  asked for "eine Chatapp in Azure mit RAG" and nothing triggered: the only trigger
  listed resource names, and a request names what the system does more often than the
  resources it needs. Workload and target terms, with German anchors, are in the entry
  description; new resource terms go into `azure-resources` only.
- **Defaults from the guardrails, not the portal — and not the module.** AVM defaults
  diverge from the guardrails too (`Standard_GRS`, 365 days retention, infrastructure
  encryption off, public access on, Key Vault `premium`, Container App ingress external),
  so every decision is written on the call even where it matches.
- **Landing-zone model.** A workload lands in an application landing zone; the platform
  (hub, DNS zones, central workspace) exists and is referenced, never built. A referenced
  hub forces the landing zone.
- **Authored rendering references target `azurerm` 5.x.** Only storage takes the string
  `public_network_access`; the others keep the bool. Several AVM modules still pin
  `azurerm` 4.x or `< 5.0` (Log Analytics, Key Vault, identity, Cosmos DB, Search,
  Container Apps environment, registry); the AzAPI-based ones need `azapi`, `modtm`,
  `random` — the root's provider set is the union.
- **Plan-only tests mock the platform.** A referenced vnet or workspace is a `data` block;
  `mock_provider` with parseable ids keeps the test credential-free (`azurerm`, `azapi`,
  `modtm`; the naming provider real; `data.azurerm_client_config` needs a GUID
  `tenant_id`). With a module in the middle the assert target is the module's `resource`
  output; what a child module builds (blob service, diagnostics, role assignments, the
  endpoint body) is not observable and is marked not-testable. A sensitive output prints
  `(sensitive value)` on failure, so the error message carries the expected value.
- **Tests are part of the render, with coverage as the contract — both targets.** One
  assert per spec decision, named by its key path, or a `not-testable` reason. Terraform
  asserts on the plan, several files, one per question-set group; Bicep asserts on the
  compiled ARM (`tests/*.armtest.yaml`, `run_arm_tests.py`, symbolic names via
  `bicepconfig.json`). `check_render_coverage.py` is the gate per target.
- **Sub-resource names go through `<?SUBNAME>`**, never appended to a finished name. The
  first cross-backend diff found `…-01-blob` against `…-blob-01`.
- **The interview is the customer's, alone** (2026-10-18; the engineer mode beside it
  dropped 2026-10-24). The `audience` field was replaced by `resolved_by` (2026-10-25):
  only `interview` questions are asked, in one batch. `platform` comes from `platform.yaml`
  (`source: platform`, read at precedence 3, never written by an interview) or opens; a
  question without `resolved_by` defaults, derives or opens. An engineer states what they know in prose and it is recorded
  `stated`; a later change is `overridden` with a reason. The plugin is public and has to
  hold for any use case.
- **Requirements live in the deployment set, the map on the resource.** Five customer
  questions (`outage_impact`, `data_loss_tolerance`, `data_access_pattern`,
  `backup_isolation`, `data_residency`) are a `requirements` group in `deployment.yaml`;
  a resource question derives through its own `derived_from: { question, map }`, so a new
  resource maps an existing requirement without touching the deployment set, and the
  default answer derives the guardrail default. The group is asked in full on every run,
  defaults included: there is no cap on customer questions (2026-10-24; multiple choice
  is cheap for the customer, a guess recorded as their decision is not). A default is not
  an assumption; a stated value holds in every stage; a parameter is never open; posture
  is one per system.
- **The decision document is rendered, not written.** Every question carries `plain`
  (`en`, `de`) and, where a raw value means nothing to a customer, `plain_values`;
  `export_decisions.py` turns the spec into `infra-decisions.md` in the customer's
  language. Word is a `pandoc` conversion offered once, never a second source.
  Customer-facing spec text (wiring labels, purposes, open questions and owners) is in the
  customer's language.
- **The picture before the code, always** (2026-10-24). Phase 5 asks the working mode
  (subagents or same session), draws the diagram as soon as the spec validates, runs the
  review loop (review agent, findings back to the diagram agent, two passes, capped at 8
  findings per pass, errors first), then shows it with the decision document and asks
  "passt das so?" — change the spec, re-export, redraw, ask again, until the yes. The
  render starts only after the yes and never touches the signed-off picture; a spec
  finding in the code loop goes back to the diagram loop. The script makes the first
  draft only; the diagram agent fixes findings **by hand in the `.drawio`**, and script
  faults become a plugin todo. No subscription frame; the resource group is the outermost
  container. One file is delivered, `infra-diagram.drawio.png`, the XML embedded.
- **Rendering with agents, two loops in sequence** (`iac-rendering/references/agents.md`):
  the diagram loop first, then the code loop (code agent, pipeline agent, read-only test
  agent, three passes, later passes re-run only the tests a fix can reach). Findings carry
  a severity and a cause; `polish` never goes back.
- **The render leaves a `CLAUDE.md` section in the customer's repository** (rule 11,
  2026-10-24): the spec is the source of truth, a code change is a spec change first,
  what regenerates from it, which checks prove the two agree; written between two markers,
  the rest of the file untouched.
- **The stack is the default, and per-stage values are never literals** (2026-10-18).
  `development`, `test`, `production` unless the customer says otherwise; a request naming
  one stage names that stage of the stack. `per_environment` values render as parameters
  from `environments/<stage>.tfvars` / `main.<stage>.bicepparam`, one state per stage by
  backend key, never a workspace; stages separated by subscription by default. Parity is
  the rule; `non_production_savings` lets `non_production_default` relax cost knobs
  outside production and the check refuses it on anything security-shaped. A `[sandbox]`
  stack takes every `non_production_default` by rule. A stage nobody could answer for is
  an `open:` entry; its stage file holds placeholders (all-zero GUID, `OPEN-<what>`) and
  the pipeline's first step refuses them.
- **The pipeline is part of the render.** `delivery` group in `deployment.yaml`
  (`deploy_mechanism`, `pipeline_auth`, `pipeline_approvals`); one reference per platform
  (`pipelines{,.github,.ado,.gitlab,.local}.md`), `check_pipeline.py` checks the
  invariants, `run_pipeline_tests.py` breaks them one at a time. The root holds an empty
  `backend "azurerm" {}` because `init -backend-config` without one is ignored silently.
  A resolved stage's file must not spell a placeholder marker even in a comment.
- **Grouped AVM calls: `granularity: per-family`** (2026-10-23, Terraform only). The root
  is `modules.<family>.tf` calls, `modules/<family>/` holds the family's AVM calls, roles,
  endpoints, tests. A module-level `depends_on` defers `data` lookups to apply, so the
  wait is an input on a `time_sleep`; a whole-module output is sensitive and infects the
  root; `mock_provider "azapi"` needs the provider in the family's `versions.tf`; a list
  output compares via `jsonencode`. A file with an authored resource starts with `res.`.
- **Naming.** Terraform uses the `LemurDaniel/naming` provider and copies `naming.yaml`;
  Bicep assembles names from `var`s and gets a `naming.yaml` only for a stated `custom`
  departure. `br/public:` needs no alias; `br/modules:` only when `bicepconfig.json`
  already has it.
- **Identity.** Container Apps and Function Apps default to a user-assigned identity
  (the first revision needs its roles before the app exists); App Service stays
  system-assigned. The Entra app registration is **not** a resource set: an `open:` entry
  owned by the identity team. `secret_placeholders` are created outside the Key Vault
  module (TF `ignore_changes = [value]`; Bicep only when the secret does not exist),
  because neither module protects the real value from the next deployment.
- **Examples are rendered, never applied, and the plugin never refers to them.** Three
  early examples were removed 2026-10-24 (owner's call); their eval cases are
  self-contained prompts and stay. The plugin's tests carry their own fixtures.
- **Evals sit in groups** (`spec/`, `diagram/`, `interview/`, `outcome/`), reach the
  plugin with `plugins: ["../../.."]`, and the baseline is accepted only after reading a
  run. The 0-cost load check proves nothing; the first paid run is the check.

## State

- **14 resource sets in 7 families**, all with both rendering references, both checks
  green: storage-account; virtual-network, network-security-group; app-service,
  function-app, container-apps, container-registry; cosmos-db; key-vault,
  user-assigned-identity; log-analytics-workspace, application-insights; foundry,
  search-service. The deployment set has 37 questions; 323 questions in total.
- **First applied render (2026-10-25): `eval-agent/`**, Bicep, one stage, deployed through its
  own rendered GitHub pipeline (what-if, approval, deploy; OIDC). The first run fed three
  fixes back into `pipelines.github.md` and `check_pipeline.py` (job without checkout,
  partial what-if, immutable OIDC subject). Not yet in the plugin: an image owned by a
  separate pipeline (`existingLinuxFxVersion`, spec decision `container_image_owner`), and
  the instance number in the unique-name seed. Terraform and the other pipelines have not run.
  Since 2026-10-25 the spec and the render (not yet deployed) split it in two: a public
  dashboard (sign-in, reads the results, holds the GitHub token) and an agent behind a private
  endpoint (runs plugin code, writes the results, no secret), on one B2 plan, one user-assigned
  identity each; the tests assert the separation (`ideas/eval-agent.md`). Open there: when the
  dashboard files a ticket (`application.ticket_trigger`), the plugin source, models, the
  sign-in secret and the image push path. The old single identity `id-…-02` and, if the first
  render was deployed, its role assignments stay orphaned until deleted by hand.
- **Three examples, Terraform only, nothing applied:** `chat-sandbox` (the first full run
  with a customer and both agent loops, authored, 118 decisions, 32 tests),
  `chatbot` (per-family AVM, 284 decisions, 79 asserted / 205 not-testable),
  `chatbot-rag` (authored, three stages, GitHub pipeline, 151 decisions, 14 open).
- **Checks:** `check_repo_consistency.py`, `check_question_set.py`, `check_spec.py`,
  `check_render_coverage.py`, `check_pipeline.py` (+ 55 cases), `run_arm_tests.py`,
  `run_diagram_tests.py`, `run_png_tests.py`, `verify_diagram.py`, `drawio_png.py`.
- **Eval baseline** (`evals/baseline.json`, 2026-10-18, $5.44): `greenfield-telemetry` and
  `private-storage-on-platform` 3/3, `vague-public-dev` 78%. Four plugin rules came out
  of the three rounds. Plugin-vs-plain measured once as a pilot (1 run per arm): 17/17
  against 15/17, the difference AVM and tests.
- **Installed on the owner's machine** (2026-10-24) at user scope, from this repo as the
  directory marketplace `infrastructure-as-skills-azure`. A directory install loads in
  place from the repo path (`claude plugin list` shows "Read from"), so an edit is live at
  the next session start or `/reload-plugins`; the copy under `~/.claude/plugins/cache`
  is only the install record. The older marketplace entry `infrastructure-as-skills`
  points at the sister repo and is unrelated.
- **The diagram grows downwards** (2026-10-24, from the first install test's render: two
  thirds empty, and too wide for a page). The services stand in two columns with a channel
  for the PaaS-to-PaaS lines, three from seven services without such lines; identities,
  monitoring and name resolution sit under the network or the services, whichever keeps
  the group shortest, referenced zones in a row below the group; the legend and the panel
  share a row under it. Nothing stands right of the services, so a dozen resources fit A4
  landscape (owner's ask: the pictures go into PDFs). The panel carries no
  prose: it counts open and assumed entries by owner and points at `infra-decisions.md`,
  which has the forced chains and the questions (owner's call, 2026-10-24). `private_with_exceptions`
  names its exceptions in the subtitle and the footer like `private` does; before, the
  footer claimed "no public access" over a public Container App.
- `docs/process.drawio.png` and `docs/process-agents.drawio.png` show the flow of
  2026-10-24, `docs/skills.drawio.png` the skills, the entry and how the units relate
  (generator in the owner's `drawio-diagrams` skill style; the PNG is the source). The
  process pair was rendered headless in a cloud session and wants one open in draw.io on
  the owner's machine to confirm it still edits.

## Open

Grouped by where the fix lands. Each item is a finding from a run or a review, kept
until it is fixed or decided against.

### Rendering references and question sets

- **azurerm 4.x spellings** in `log-analytics-workspace`, `app-service`, `foundry`
  `terraform.md` and ~50 `renders` lines: `internet_*_enabled`,
  `local_authentication_disabled`, `*_basic_auth_enabled`, `legacy_access_policies_enabled`,
  "use azapi" for Foundry projects. 5.x has `internet_ingestion_access_type`,
  `local_authentication_enabled`, `ftp/webdeploy_publish_basic_authentication_enabled`,
  `azurerm_cognitive_account_project`.
- `terraform.md` tables stale in places: `log_categories` for the Key Vault, Search,
  Foundry, ACR, Cosmos DB and NSG modules. Diagnostic category names in several sets are
  from memory (Key Vault, Cosmos DB, Foundry, App Service, Search) and want
  `az monitor diagnostic-settings categories list` against a real resource.
- `storage-account.private_endpoint_subresources` has no `depends_on` and lands in a spec
  without a network. `foundry.restrict_outbound: true` has no `allowed_fqdns` question.
- Function App's per-plan subnet delegation is from memory; Container Apps session pools
  have no set; a container's throughput in Cosmos DB is one value for all; the Foundry
  project API version is a placeholder; the NSG baseline rules per `subnet_purpose` are
  general knowledge, to be confirmed per service before a render; a closed Application
  Insights needs the platform's Azure Monitor Private Link Scope. The Key Vault modules'
  `keys` member names are read from the README at render time.
- Missing sets: `recovery/backup-vault` (so `backup_isolation: isolated | immutable`
  renders instead of being named as missing); blob container, file share, queue; a
  resource lock decision; a pipeline guard that checks a stage's `location` against
  `data_residency`.
- `app-service` renders one site per plan; two apps on one plan (`eval-agent/`) are a
  hand-rendered plan and site, noted in the spec. Either the set gets a `plan` decision
  (own plan or shared with an instance) or a pattern owns the shared plan. A second app also
  needs a private endpoint subnet decision per instance and `privatelink.azurewebsites.net`
  in `wiring.private_dns_zones`, which no rule adds.
- Bicep: no per-family shape in `bicep-idiom.md`; the sets from 2026-10-23 have no Bicep
  render at all; `*.armtest.yaml` is one file per example.

### Interview and spec

- The deployer's roles are not in the spec: a non-empty `key-vault.secret_placeholders`
  needs Key Vault Secrets Officer, rendered role assignments need RBAC Administrator;
  neither derives from `pipeline_auth`. The interview should add them, `pipelines.md`'s
  hand-over list the data-plane roles.
- `chat-sandbox` has no `open:` entries for `subscription_id` and `resource_group_name`
  although its stage file holds placeholders for them.
- `check_spec.py` does not know `granularity: per-family`; all three example specs say
  `single`, `chatbot` is per-family. `wiring:` is validated by example only.
- `export_decisions.py` prints `reason` and `open:` texts untranslated; "1 Kopien der
  App" needs a singular form. `infra-decisions.docx` is missing everywhere (no `pandoc`).
- The extension run that writes a further stage's file once its `open:` entries are
  answered has not been exercised.
- **Resource groups: the contract stands, the render does not** (2026-10-25). Done: the
  `resource_groups` group in `deployment.yaml` (split, a mode per role, lock), the `contains`
  condition in `check_question_set.py`, `references/resource-groups.md`, the role table
  `resource-group-roles.yaml` (read by the diagram and the decision document), `spec.md`
  ("Resource groups: roles, modes, names"), `check_spec.py` with
  `iac-authoring/tests/run_spec_tests.py` (one broken rule per case), the diagram (a tag per
  service zone, support zone, network and monitoring zone framed per group, compute tagged) with fixture
  `resource-groups-split.yaml`, `resource-groups-small.yaml` and three cases, the "Ressourcengruppen" table in
  `export_decisions.py`, pipelines.md invariant 12 with a step in the four Terraform pipelines,
  `check_pipeline.py` and four mutations, and `examples/chatbot-multi-rg` (spec, diagram,
  decision document; not rendered). Open, in the order they block a `create` root:
  - **Bicep pipelines deploy with `az deployment group`** (`pipelines.github.md`, `.ado.md`,
    `.gitlab.md`, `.local.md`); a root with a `create` group has `targetScope = 'subscription'`
    and needs `az deployment sub`, and the stage identity Contributor on the subscription. The
    pipelines reference lists neither.
  - **No render of a split**: no example has Terraform or Bicep for it, so the Terraform
    `assert`s, `run_arm_tests.py` and `check_render_coverage.py` do not cover a group decision
    (`# decision: deployment.resource_group_mode_<role>`, `<resource>.placement.resource_group`).
    `chatbot-multi-rg` is the candidate.
  - **The `jq` filter of invariant 12 is unproven**: it never ran against a real plan JSON, so
    its `azurerm_resource_group` and `azapi_resource` branches (does the AVM resource group
    module create the group as `azapi_resource`, with `Microsoft.Resources/resourceGroups` in
    `change.before.type`?) are assumptions; the tests only assert the step is in the text. The
    GitLab example also assumes `jq` in `mcr.microsoft.com/azure-cli`.
  - **The name of a created group** (`rg-we-prod-payments-data-01`: workload plus role as the
    name segment) is not checked against `naming.yaml` or the naming provider.
  - **Bicep never deletes a group**: dropping one from the spec or switching `create` to
    `existing` leaves it orphaned. The hand-over should say so; nothing does yet.
  - **A mode or role change is not announced**: the CLAUDE.md block tells the render to read the
    plan first, but `iac-authoring` has no step that detects a carried `resource_group_mode_*`
    or `placement` that changed and names it before writing.
  - **No eval case** for a split, nor for "spec exists, the user changes one value".
  - **`export_decisions.py` has no test of its own**; the groups table was checked on the
    example only.
  - **The diagram frames a group only where its resources stand together**: the services, the
    support zone, the network and the monitoring zone. Compute sits in the network's subnets and
    gets a tag; more than eight services in the compact layout fall back to tags too. Frames of
    different groups can leave blank space (a frame is as tall as its tallest label).
  - **Plugin todos from the 2026-10-25 diagram reviews** (the four examples were re-rendered
    through review and diagram agents; `new_diagram.py` was not touched in the loop). Two pictures
    still carry a finding after two passes: `chat-sandbox` (`e-7`, the label "liest das Client
    Secret" sits beside its arrow, not on it) and `chatbot-multi-rg` (`e-14`, the telemetry line
    now runs through the "Identities and network baseline" zone). The hand edits of
    `chatbot-rag`, `chat-sandbox` and `chatbot-multi-rg` live only in the PNGs; a regeneration from
    the spec loses them. Script faults behind the findings:
    - a target below the zones is reached by a detour through the private endpoints' trunk (or,
      when hand-routed, through another zone) - the corridor belongs left of the trunk;
    - edge labels sit in the middle of a line and land on frame borders - offset them, or move
      them onto a drop outside the frames;
    - actor lines on one side of a target and every top-to-top edge share one track;
    - the slot order ignores which services call each other, so lines cross (sort by edge
      adjacency, stagger actor lines by the target's height);
    - the Monitoring zone title reads "Monitoring · monitoring (created)" with a split - name the
      group once;
    - the legend has no entry for purple role text or the orange public-access warning, and the
      decisions panel prints raw spec values ("Netzwerk: none", "Private DNS: deployment");
    - the legend line "existing, not created here" next to a dashed network group frame reads as
      "this run builds none of it" although the group exists and its contents are created.

### Pipelines

- `check_pipeline.py` counts an `open:` entry without `environments` as resolved (a false
  fail on every such entry; the runs name the stage on each entry as a workaround),
  applies the workload-identity secret grep to `local`, and its `client[-_]?secret`
  pattern matches the placeholder name `entra-client-secret`.
- `pipelines.local.md`'s script runs `validate` after the backend init, has no
  `terraform test`, no `-reconfigure`, no cd to its own directory; `terraform-idiom.md`
  says the empty backend block is for non-local only, but the local script passes
  `-backend-config` too.
- `pipelines.github.md` says nothing about a render in a subfolder (working directory,
  artifact paths, path filters) and pins Terraform `~> 1.16.0` (live 1.17). GitLab has no
  scaffold behind it and is untested; Azure DevOps and GitLab accepting their file was
  never checked.
- `naming.tftest.hcl` proves "from naming.yaml", not the deployed suffix, while the stage
  file holds placeholders. `terraform providers schema -json` refuses a root with an
  empty backend block unless run on a copy without it. `terraform init` fails on the
  Windows path limit in a long scratch path (`subst` does not help): a render sits at a
  short path before `init`.

### Diagram

- `new_diagram.py` faults from the reviews: the search → foundry edge runs through the
  key vault icon, the app's edges merge into one bus with stacked labels, shared anchors,
  branch labels on the trunk, the law subline, the role-count line. draw.io's library has
  no icon for Foundry or Container Apps (nearest used).
- `iac-diagram/SKILL.md` still says the search → storage line is not routed; the default
  NSG pattern has no `<?SUBNAME>` (two NSGs got one name); the web app name has no unique
  id (global hostname); `wiring.private_dns_zones` lacks `oms`/`ods`/`agentsvc` for a
  monitor scope; the Key Vault has no caller in the picture until its access is decided.
- `chat-sandbox`'s decision panel was finished by hand before the two SKU corrections and
  does not list the new forced chain (`verify_diagram.py` passes).
- Not exercised: a fresh export through `export_diagram.py` end to end; the customer-edit
  diff path (extract, regenerate, diff).

### Agents

- `agents.md` lacks a severity *not checkable* (a reviewer counted an unverifiable number
  as an error) and the rule one cause per finding.
- The evals were not re-run on the sign-off-first flow or the module-choice question.

### Diagram generator

The three example diagrams went through Loop 1 with subagents on 2026-10-24 (11 errors in
pass 1, 0 in pass 2); every error was a generator fault and was fixed in `new_diagram.py` the
same day: anchors spread per icon side (0.7 / 0.3) with the trunk entering at 0.3 beside
them, labels beside their own segment and above a straight run, the trunk leaving over the
top when actor lines end at the icon, a PaaS-to-PaaS line without the network routed over
the row, the network red over open addressing, `wiring.purposes` on the workspace, a
localised group label with the stages, data-plane roles and endpoint subresources counted,
principals by display name, one blue legend row, telemetry in blue, a mark on a public
exception.

**Second round, open (owner's call 2026-10-24: later).** The three examples were regenerated
with the fixed generator and reviewed again: 10 errors (chat-sandbox 5, chatbot 1,
chatbot-rag 4) against 11 before, so the first round closed as many as it moved. The
committed example PNGs are the hand-finished ones from Loop 1, not the regenerated drafts.
What the second review found, all `render`:

- Actor lines: tracks are assigned by actor height, so the line to the farthest actor
  turns on the innermost track and crosses the others; assign tracks by distance from the
  compute (farthest actor, outermost track). Their labels now stack at the three arrowheads;
  put each label above the segment at its own actor, where no other line runs.
- Hub layout: the caller's line into the endpoints leaves at 0.5 while the users line
  enters at 0.5 (one line through the App Service); leave at 0.7 when actor lines end at
  the icon, as the bus layout already does. The trunk into a first-column service enters at
  0.3, but the PaaS line leaving it can be at 0.3 too (second anchor on that side): pick
  the trunk's height from what the icon's sides do not use.
- Caller lines cross each other in the collector corridor (chatbot: four crossings between
  web→mcp, mcp→container-apps and the e-in lines); the track assignment ignores the
  compute-to-compute lines.
- Labels: a PaaS-to-PaaS label on the vertical in the channel has the line through the
  word - put it above the line's first horizontal, at the source; the bus-layout trunk
  label lands at the junction, not on the drop, because the label fraction is computed
  from the right-edge exit while the line leaves over the top; a label beside a track with
  offset 8 + 3·chars reaches the next drop; "HTTPS 443" straddles the network border.
- Without the network, the PaaS-to-PaaS run over the row crosses the trunk drops; give
  the edges `jumpStyle=arc` so a crossing reads as a crossing.
- Role lines wrap in the 162px slot and read as twice as many entries: bold the principal,
  or widen the slot for icons with roles. The legend has no row for the purple role text
  and the orange public mark.
- Panel: skip the "Private DNS" line when the spec has no zones; the legend-beside-panel
  threshold (380px) keeps them stacked on a 850px group - 300 is enough for eight lines.

**Plugin todos from the 2026-10-25 review of a spec with a second App Service** (an
`app-service__mcp` added to a bicep spec of eight resources; review agent plus hand edits in
the `.drawio`, `new_diagram.py` not touched). The picture's hand edits live only in the PNG: a
regeneration from the spec loses them. All `render`:

- **Done 2026-10-25** (`new_diagram.py`): role lines dropped (the label carries them), a compute -> compute
  line between two icons of one row runs side to side, the public exception names the instance
  ("App Service · dashboard"). The other four of this list are open.
- **Role lines run through icons.** `wiring.role_assignments` draws one line per role from the
  identity to each target with no waypoints, and draw.io routes them: straight along the
  identity's row through the monitoring and DNS icons, up a trunk through the endpoints' icon
  and label, through the "Namensauflösung" title, across the Key Vault icon to reach Storage,
  and ending on the Registry and Key Vault icons. The first finding of the review, and the owner
  saw it at once. The hand fix deleted the four edges (the targets' text already says
  "← Managed Identity: <role>"). Do the same in the script - drop role lines when the target
  text carries the principal and role - or route them through the free strip between the
  network's bottom and the zones' top (a 16px corridor: the network ends at y 394, the zones start at y 410) and enter each
  target from a side no other line uses; at minimum never leave a role edge without waypoints.
- **A caller behind a caller.** With two compute icons in a subnet the first caller's line to
  the endpoints passes behind the second icon (same row, exit at 0.5). Offset the second icon's
  row, or leave the first caller over a lane that the second does not occupy; the hand fix moved
  the MCP icon 38px down and routed `dashboard -> mcp` from the right side to the left. Seen
  again on `eval-agent/` (2026-10-25): the users line ran through the first icon to reach the
  second, and both callers' lines to the endpoints ran behind the second icon. The hand fix put
  the actor-facing app first, moved both icons 14px down, routed that app's endpoint line over
  a corridor above the icons, and widened the subnet; a regeneration loses it.
- **A compute-to-compute line goes top to top.** `e-5` (`dashboard -> mcp`) is drawn as a loop
  over both icons, its label lands on the subnet header ("delegiert an …"), and the straight
  line between the icons reads as a second connection. Route it side to side and put the label
  above its first segment.
- **Subtitle and the green group line say "App Service" in the singular** when one of two App
  Services is public. Name the one that is (`wiring.purposes` entry or instance name), as the
  icon label already does.
- **"HTTPS 443, …" straddles the group border again** (see the second round above). Break the
  label into two lines and put it above the segment at its actor.
- **The instance names `app-service__web` / `app-service__mcp` work in the picture** (icon,
  title and purpose are taken from the set before the `__`), but the "Private Endpoints" bundle
  reads "5× App Service, Container Registry +3": count and name instances, e.g. "App Service
  (mcp)", so the reader sees which of two has an endpoint.

### Evals

- No case covers triggering. The one failure a real run has shown is a workload-shaped
  request ("eine Chatapp in Azure mit RAG", no resource named) that opened no interview;
  a case with that prompt and an llm grader on the first message (interview opened, the
  customer sentence said, no home-made questionnaire) is the regression test, and the
  no-plugin baseline arm shows what it is measured against.
- No grader checks `implementation` or `module_source`. No case for: the delivery
  questions; an engineer-flavoured request asserting no `engineer` question is asked;
  the whole `requirements` group reaching the customer (the gap of 2026-10-24); the
  customer-question graders (question count, Azure vocabulary in the questions,
  readability).
- `vague-public-dev` at 78%: both causes are plugin rules written after the baseline. The
  next full run (~$5) should lift it; accept with `--update-baseline` after reading it.
- The plugin-vs-plain pilot needs 3 runs per arm and cases on the small decisions
  (replication, soft delete, infrastructure encryption, SFTP), ~$15-25, before it counts.
  `terraform validate` in an eval needs a Linux runner; the spec-graded cases cannot run
  without the plugin.

### Waiting on the owner

- A sandbox subscription with a federated credential and a fenced resource group for the
  deploy agent (`ideas/autonomous-terraform-agent.md`). The first apply ran in the owner's
  own subscription (`eval-agent/`); a fenced sandbox is still missing.
- `patterns/` is empty: composition is specified and proven by two hand-wired examples
  only (`ideas/pattern-skill.md`).
- An AVM version drift check, read-only, scheduled (`ideas/avm-drift-watch.md`).

### Environment

- A cloud session needs `registry.terraform.io`, `releases.hashicorp.com`, `github.com`
  release downloads and `mcr.microsoft.com`, and installs `terraform` and `bicep` into
  `~/.local/bin` itself. No Linux in WSL on the owner's machine.

## Next

**The pattern skill** (`ideas/pattern-skill.md`): the wiring that `chatbot` and
`chatbot-rag` carry by hand — roles between resources, the private link, the order
identity → vault → consumer — becomes the first pattern, `./patterns/` enters
`plugin.json` in the same commit, and `wiring:` becomes a schema `check_spec.py` validates.
Before it, the two small items from 2026-10-24: the `recovery/backup-vault` set and the
eval case that asserts the `requirements` group reaches the customer. Beside it, when a
run is paid for anyway: the eval suite re-run against the rules written after the
baseline, and `agents.md`'s two missing rules. The chatbot case in Bicep is what tests the
sets from 2026-10-23 cross-backend; it follows the pattern, not the other way round.
