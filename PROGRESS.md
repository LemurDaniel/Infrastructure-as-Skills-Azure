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
- **A resource lock is a decision of its own** (2026-10-25): `deployment.resource_lock`
  (`production` by default) puts `CanNotDelete` on the resources whose loss cannot be undone
  from the spec - the list is in `avm.md` - through the `lock` interface every AVM module has.
  Compute, identities and network resources carry none: they are recreated from the spec, and a
  lock on a virtual network blocks changing its subnets. It is not the resource group's lock.
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
  only `interview` questions are asked, in one batch. `platform` is never asked: derived from the landing-zone questions
  (`landing_zone_exists`, `central_*`; no `platform.yaml`, 2026-10-26) or opens; a
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
- **A render writes infrastructure only** (2026-10-27, `iac-rendering/SKILL.md`, "What a
  render may write"): Terraform/Bicep with tests and stage files, the spec's render fields,
  pipeline files and the `.ps1` they call, `.gitignore`, the `CLAUDE.md` section. Application
  code (`.js`, `.ts`, `.cs`, `.py`, `package.json`, `Dockerfile`, app config) is never
  touched, also inside the render root; a mismatch is named in the hand-over. The boundary is
  by file type, not by directory: a run's code agent, briefed with "the render root only",
  edited Node.js code that lay inside it. Same session and every agent; the review and test
  agents route an app-code finding to the hand-over only. Not enforced by a hook - text only.
- **The render leaves a `CLAUDE.md` section in the customer's repository** (rule 11,
  2026-10-24): the spec is the source of truth, a code change is a spec change first,
  what regenerates from it, which checks prove the two agree; written between two markers,
  the rest of the file untouched.
- **The section is versioned and synced by the skills, not by CI** (2026-10-25): the text is
  `iac-rendering/references/claude-md-block.md`, `rev=<n>` in its begin marker, written by
  `sync_claude_md.py` (or by hand without a shell). A lower rev is replaced, the same left, a
  higher one never overwritten (no downgrade) and the person told the plugin is old; a damaged
  marker pair is left alone; the script always exits 0. `claude-md-block.lock` pins rev and
  text hash so the plugin repo cannot change the text without a new rev (`check_repo_consistency.py`).
  `iac-authoring` runs the sync before its first question where a spec exists. rev 2
  (2026-10-27) adds the write boundary for later infrastructure changes in the customer repo.
- **`spec.plugin_version` halts an older plugin** (2026-10-25): the plugin that last wrote a spec
  stamps its version; a plugin older than that renders nothing, writes nothing and asks once
  (AskUserQuestion) to update with `claude plugin update`, restart required; there is no way on
  with the older plugin. A spec without the field is not held back, a malformed one is ignored.
  `check_plugin_version.py` exits 3 for the halt. Evals: `sync/plugin-newer-halts` and
  `sync/claude-md-section-replaced`; the no-downgrade rule is script-tested only, an eval costs too much.
  The example specs carry no `plugin_version` yet; the next write stamps them.
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
- **Pipelines run PowerShell 7, not bash** (2026-11-01, invariant 14). Bash was never a
  decision, only the runner default copied from vendor docs; the stack is pwsh, both hosted
  Ubuntu images ship it, JSON is read with `ConvertFrom-Json` instead of `jq`. Not a spec
  question: a fixed default. GitLab stays `sh` - its job images carry no pwsh.
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
- **Evals sit in groups** (`spec/`, `diagram/`), reach the
  plugin with `plugins: ["../../.."]`, and the baseline is accepted only after reading a
  run. The 0-cost load check proves nothing; the first paid run is the check.
- **An identity exists only for an outward reach** (2026-10-26): the default of Foundry, AI Services, storage account and Communication Services is `none`, as the container registry's already was; their `why` said so and the default contradicted it. Callers use their own identities, so an unused system-assigned identity is a principal to track for nothing. Customer-managed keys still force `user_assigned`. The eval agent's Foundry and storage account were re-rendered without one (first seen there: the apps' roles are on the apps' identities, the accounts hold none).
- **The batch is asked in topics, the security baseline is shown as a block** (2026-10-26): every interview question carries a `topic` (`platform`, `network`, `security`, `resilience`, `data`, `application`; the checker fails without one), Phase 3 asks topic by topic and cuts the `AskUserQuestion` call at the topic, not at four. Phase 4 shows the guardrail defaults of the `security` and `identity` groups as one block grouped by what they protect, with a sign-off option for a departure; `export_decisions.py` groups them the same way. Reason: the security questions never reach the customer, so the one place they can be seen is the list before the sign-off, and it had been one line. Not yet seen in a run; the interview evals predate it.
- **`priority` moves cost and hardening, never the security floor** (2026-10-26): a seventh `requirements` question - `cost`, `balanced` (default, the guardrail baseline), `protection` - asked of the customer. `protection` forces `non_production_savings: disabled` and derives the records an investigation needs (storage change feed, network flow logs); `cost` equals `balanced` for the knobs wired so far, since the baseline is already lean there. A named requirement (outage impact, retention, a mandate) wins over it. Open: more knobs to wire, above all ones that make `cost` differ from `balanced` (SKU tiers, zone redundancy of plans, registry and search tiers); Key Vault has no cost knob worth a mapping, DDoS is a `platform` decision. Not seen in a run.

- **The platform is asked, not read from a file** (2026-10-26; `platform.yaml` removed).
  `landing_zone_exists` and `network_exposure` are interview questions; `landing_zone` is
  derived (`corp` private, `online` public, `sandbox` from the stage answer, `standalone`
  without a landing zone). Without one, `central_logging`, `central_private_dns` and
  `central_network` each set their own ownership decision, and an explicit answer beats an
  archetype's pre-answer; `central_backup` is asked beside them. Names behind a "yes" are
  stage parameters or `open:` entries for the platform team. `resolved_by` is `interview`
  or `derived` (never asked). `private_with_exceptions` asks `public_parts` and
  `public_audience`; one list question, `resource_groups_created`, derives the per-role
  modes the spec keeps.

- **The spec has a canonical form, laid out by a script** (2026-10-26): the run decides,
  `write_spec.py` writes the layout - deployment keys in `deployment.yaml` order under a
  `# --- <group> ---` comment per group (layout only, the path stays `deployment.<id>`), a
  resource's questions in its set's order, a decision on one line when it fits in 120
  characters, no anchors, `plugin_version` stamped. Resources keep the run's order: the
  decision document, the name list and the picture follow it. No value changes and no
  comment is lost (comments carry quoted customer answers and `overridden` reasons), or the
  file is not written. Before, the model typed the file and every example looked different
  (anchors in `chatbot`, maps vs. scalars, block vs. one-line entries). Learned from
  comparing with github/spec-kit; nesting the deployment groups was rejected for the
  hundreds of `deployment.<id>` references it would move.

- **Region, subscription and resource group: never asked, never invented** (2026-10-26).
  Stated in the request, they are recorded and go into the stage file; not stated, each is an
  `open:` entry (workload owner, `blocks: apply`) and a placeholder in the stage file
  (`OPEN-location`, the all-zero GUID, `OPEN-resource-group`). A `create` group needs no
  name. Before, the rule said "never an open item", and runs filled the gap with a plausible
  `westeurope` that read as a decision. `check_spec.py` warns (not errors) on a value that is
  neither: a filled-in stage file carries it without the spec.
- **Only the Foundry account may run in another region** (2026-10-27, owner's call: an edge
  case, not a general mechanism). A model `context.location` lacks is first tried as
  `DataZoneStandard` there; only then `resources.foundry.placement.location` (Sweden Central
  the usual one), named by the person with the model as the reason, one region for every
  stage - regions per stage make no sense. Refused under `data_residency: country`. The
  private endpoint stays in the network's region and is written explicitly: the Terraform
  AVM module otherwise puts it in the account's region (checked in `main.privateendpoint.tf`).
  Agent network injection needs the account in the VNet's region (Microsoft Learn), so it
  rules the departure out. The names are unchanged: the account's pattern has no region.
- **Foundry models come from a generated catalogue, never from memory** (2026-10-28, owner's
  call). A run offered gpt-4.1 (Legacy) while gpt-6 was GA. `resources/ai/foundry/models.yaml`
  is written by `.github/scripts/update_foundry_models.py` from the EU regions' catalogue and
  refreshed monthly by `refresh.foundry-models.yaml` (identity of the `production` environment, a PR
  with a patch bump when it changed); no CLI in the user's session. The question field
  `accepts: { catalogue: models.yaml }` carries it into the digest. The interview asks family first (multi-select),
  then per family its three newest models (multi-select, "Noch offen" first), the embedding
  model as a single choice; a family outside the residency answer is put back, never widened.
- **Application telemetry goes to Application Insights by default** (2026-10-28, owner's call).
  `deployment.application_monitoring` (default `enabled`, not asked, a Phase 4 row) brings one
  workspace-based component per stage for the whole system when there is an App Service,
  Function App or Container Apps; each application's `application_insights` is forced to it
  (app setting or container env). `check_spec.py` fails on `enabled` with an app and no component.
- **Application Insights is reachable from the internet by default, like its workspace**
  (2026-10-29, owner's call). It inherited `network_exposure`, so a private deployment closed
  it - but a closed component needs an Azure Monitor Private Link Scope, which a standalone
  deployment never has, and received no telemetry behind an `open:` entry blocking apply. Now
  `public_network_access` defaults to `enabled` (ingestion authenticated by Entra ID); `disabled`
  only for a stated AMPLS. Seen in a diagram: the workspace marked public, the component not.
- **The plugin owns the infrastructure, not the application** (2026-10-28, owner's call). What
  the code does - sign-in implemented in a container, the Application Insights SDK - is not
  asked, flagged or opened; platform features (a component, a connection string, Easy Auth if
  ever wanted) are the plugin's.
- **Feature -> `dev` -> `master`; every merge into `master` is a release** (2026-10-26,
  owner's call; `dev` added 2026-11-01, owner's call). `dev` exists so the eval agent can be
  deployed without a release: a push to `dev` runs `eval-agent-infra.yaml` and
  `deploy.eval-agent.dashboard.yaml` into `production`, a push to `master` deploys nothing.
  `master` stays the default branch, because the marketplace reads it - a user installs
  only what is released. Feature branches go into `dev` as a squash merge and raise no
  version; `dev` goes into `master` by a release PR as a merge commit (never squash, or the
  two histories part), which raises the version once. `check.pull-request.yaml` runs the checks on
  both; into `master` it also fails unless the head is `dev` and `plugin.json`'s version is
  newer than the last tag and `master` (`check_version_bump.py`). `release.plugin.yaml` runs on the
  push to `master` and creates tag and release itself. No tag by hand.
- **The question-set format, revised** (2026-10-28, branch `restructure-core`):
  `accepts` is the one field for what an answer may be - a value list, `{ ref: <kind> }` or
  `{ catalogue: <file> }`; `values`, `ref`, `options_from` and `type: ref` are gone, the type
  says one or many. `ask` carries `en` and `de` like `plain`, so the interview reads the
  customer's question instead of translating it anew each run. `confirm_in` is gone: a
  "please confirm" in a document the customer skims changes nothing - what the customer can
  judge is asked or derived from a requirement. A question that inherits its answer is never
  `interview` and repeats `derived` from its source (checked). `answer` is the one field for an
  inherited value - `{ deployment }`, `{ context }` or `{ question, map }`. There is no engineer role:
  open items belong to the workload owner or the platform team.
- **The spec format, revised: what is derived is not written** (2026-10-29, branch
  `restructure-core`, owner's review of `spec.md`). No migration path - nobody but the owner
  uses the plugin; the repo's specs were moved over, `check_spec.py` refuses the old forms.
  - `source` is a word or a map of one key that names the kind and its pointer:
    `{ forced_by: ... }`, `{ derived_from: deployment.<id> }`, `{ overridden: <reason> }`;
    no `forced_by:`/`derived_from:`/`reason:` beside it. One field says where a value came from.
  - Every map in block style, a stage map one stage per line; only a short list of plain
    values stays on one line - the one-liners with nested braces were unreadable.
  - `resources.<key>.meta.purpose` replaces `wiring.purposes`: a purpose belongs to its
    resource, and `meta` holds what describes rather than decides. `wiring.optional` is gone:
    a part nobody decided on is an `open:` entry, a resource in the spec is built.
  - `non_production` is gone: which stages took the cheaper default follows from the
    question, `non_production_savings` and the values; the decision document derives it.
  - Resource groups: `resource_group_split`, `resource_group_components` and every
    `resource_group_mode_<role>` are gone. The groups follow from layout, scheme and each
    resource's role (`rg_roles.groups`); a split has no main group (the partial split with
    `main` beside listed roles is gone); `resource_groups_created` is the one record of what
    the render creates. A group nobody wants goes by placing its resources elsewhere.
  - A `per_environment` value from outside the spec (range, id, platform part) must be a
    stage map even when the stages agree; one naming only the spec's own parts stays one value.
  - An `assumed` value renders as a stage-file parameter with its working value and an
    `ASSUMED: <key>` marker; the placeholder guard (invariant 11) refuses it, so `plan` runs
    and `apply` does not - before, nothing technically stopped an assumed value deploying.
  - The Shape example of `spec.md` is tested: it must pass `check_spec.py` and be canonical.
- **GitHub Copilot CLI is the second host, Codex is not** (2026-10-29): Copilot reads the
  `.claude-plugin/` manifests as its legacy format, `"skills": ["./core/"]` included - all
  four skills load and the interview asks through its own question tool, with no change to
  the plugin. Azure customers sit on Copilot licences; Codex reaches few of them and has no
  eval harness here. An Agent Plugins 1.0 root `plugin.json` would serve both, but fixes
  skills to `skills/` - not worth moving `core/` for until a host needs it.
- **What a decision renders to is data, `render-map.yaml`, read through a digest**
  (2026-11-01). A render read the skill, `spec.md` and every reference whole (~250 KB) and
  took the attribute from the question's `renders` string - prose, partly stale (azurerm 4.x
  names, inverted polarity, the authored spelling under AVM: `account_replication_type` where
  the module takes `account_sku_name`). Now each resource has a `render-map.yaml` beside its
  set: per target and implementation the attribute and the literal of every answer
  (`references/render-map.md`); `render_digest.py <spec>` prints each decision with that
  literal filled in, plus the line ranges of only the references the spec needs (~50% less
  read). Data, not prose, because the renderer's core must not rest on heuristics: the digest
  does `dict` lookups, `check_render_map.py` holds every file to its question set. A literal
  no reference states is a `gap`, never a guess; every scalar answer says how it renders
  (`values` complete, `format`, or an explicit `passthrough: true`) - the pass-through of an
  answer into an id, a block or another unit was the error class the reviews found most. YAML
  in its own file, not in `questions.yaml`: the set stays backend-neutral, as the spec does.
- **A reference is `{ resource: <key> }` or `{ existing: <kind> }`, its kind registered**
  (2026-11-01). `accepts: { ref: <kind> }` named a bare word, and a spec held a reference in
  five shapes - key, plain name, id, `{ name, resource_group_name }`, a stage map of any - told
  apart by a regex; nothing checked a value was of its kind. Now
  `core/iac-authoring/references/ref-kinds.yaml` defines every kind (the sets that create it,
  the part where it is one, the ARM type and form of its id: `arm`, `arm_any`, `guid`), and a
  spec writes a resource of the spec as `{ resource: <key>[, part: <name>] }` (one value, every
  stage; a subnet is a part of the network) or one outside it as `{ existing: <kind> }`.
  **The spec carries the id, never a name or a resource group** (owner's call): an id the
  person gives goes in per stage (`id: { <stage>: <id> }`); without one an `open:` entry names
  the owner and the stage file holds a placeholder id the pipeline refuses before `apply`.
  **Rendered as an id variable / param, never a lookup**: a data source needs a name and a
  group as unknown as the id, and makes every `plan` read the platform; the id in the stage
  file pins nothing into the code, and tests pass it as a variable instead of mocking a data
  source. `scripts/spec_ref.py` reads both forms for `check_spec.py`, the diagram, the
  decision document and the digest. Kept outside the rule on purpose: the resource groups
  (named in `context`), the private DNS zones (a fixed name in a group) and the Network
  Watcher (Azure's fixed name). Front Door's origins split into `origins`
  (`{ ref: resource }`) and `origin_host_names`, a backend outside Azure having no id.

## State

- **`render-map.yaml` for all 67 resources, the render digest mandatory** (2026-11-01, branch
  `render-yaml`): 5,190 entries, 980 of them `gap` (18% - the references do not state the
  literal), 1,658 explicit pass-throughs, 101 `not_rendered`. Written by 8 agents, reviewed by 3
  (330 ERRORs - the hand-written storage pilot had 9), corrected by 8, sample-reviewed once more
  (75 of 81 former ERRORs fixed or honestly a gap, the 6 left fixed by hand, 0 unit errors new).
  `check_render_map.py` and both test runners are in the repository checks. The format has
  `companions`, lists per attribute or module, `kinds`/`by_kind`, composite formats with
  `part_of`, `format: { expr }`, `omit_empty`; code names `{group.question}` (filled by the
  digest) and `<name>` (filled by the render), never `...`; `authored_when` names the answers a
  module refuses, which render the resource authored. The map is the one record: `renders` is
  gone from the resource sets (the check refuses it there; the deployment set keeps its own),
  and the references' decision tables are gone, their remarks moved into the maps.
- **18 more sets written 2026-10-26 (67 resource sets in 10 families, 1,442 questions with the deployment
  set), checked, not exercised:** network public-dns-zone, traffic-manager, ddos-protection-plan, network-watcher (VNet flow logs only);
  observability action-group, alert-rule (metric, log query and activity log by `kind`),
  data-collection-rule (+ endpoint); messaging event-grid-namespace, event-grid-system-topic,
  relay-namespace; data sql-managed-instance, data-factory, purview-account; integration logic-app
  (Standard and Consumption by `hosting`), communication-services; ai ai-services (one kind per
  account), machine-learning-workspace, bot-service. Written by six parallel agents from one brief,
  each call validated with `terraform validate` against the pinned module (or authored azurerm 5.x
  where none exists: system topic, metric and scheduled-query alerts, Purview, management group,
  Communication Services) and `bicep build`; no render, test or eval covers them. Three governance sets (policy, management-group, subscription; ownership decision from the platform
  profile, nothing rendered by default) were written the same day and **parked outside the plugin in
  `drafts/governance/`** (owner's call: not shipped for now; they pass the format check and their calls
  validated, nothing in the plugin refers to them). Shared tables are
  updated: `avm.md` rows, `resource_lock` list (+ event-grid-namespace, sql-managed-instance,
  purview-account, public-dns-zone), `resource-group-roles.yaml`, `naming.default.yaml` (ddos, dnsz, rn, ma, sqr, ala, bot default), `new_diagram.py` ICONS/TYPE_NAMES (paths checked
  against the draw.io source tree; Purview, the Event Grid namespace, the system topic and the action
  group borrow the nearest icon), the `azure-resources` description (1,700 of 2,000 listing budget,
  85% - the next family's terms need pruning first). Open from the writing: `learn.microsoft.com` is
  unreachable from a cloud session (proxy), so the diagnostic categories of the network, observability
  and ACS sets come from the Azure Monitor docs source on GitHub or product knowledge and every set
  says to check them live; the `virtual-network` set's `ddos_protection` bool has no plan reference
  and its `flow_logs_enabled` should point at `network-watcher`; `data_location` of Communication
  Services is a required open entry because a `derived_from` map cannot depend on the region; the
  Terraform site module cannot render identity-based host storage for a Standard logic app; the
  alert, DCR and flow-log kinds count as `MONITOR_KINDS` in the diagram but have no layout of their
  own.
- **Release 0.1.0 (2026-10-25), the first stable one** (owner's call): `release.plugin.yaml` marks only `0.0.x` and
  suffixed versions as prereleases. The plugin folder has its own `README.md` (the directory reads it, with what the plugin
  runs and writes), `displayName` and new keywords are in `plugin.json`. Not done: the submission to Anthropic's plugin
  directory (developer portal, `claude.ai/directory/manage`; needs the owner's account, GitHub connection and the
  Software Directory Policy read - not read by a session), a plugin icon, a re-run of the evals against the rules written
  after the 2026-10-18 baseline.
- **24 more sets written 2026-10-25 (49 resource sets, 1,044 questions with the deployment set), checked, not exercised:** compute
  virtual-machine, managed-disk, availability-set (the proximity placement group is a question
  group of it), virtual-machine-scale-set, aks, static-web-app, container-instances; network
  public-ip-address, private-endpoint, private-dns-zone, route-table, nat-gateway, azure-firewall,
  load-balancer, bastion, virtual-network-peering; data sql-database, postgresql-flexible-server,
  mysql-flexible-server, redis-cache (Azure Managed Redis only, not the older Azure Cache for Redis);
  security role-assignment, key-vault-key, key-vault-secret, defender-for-cloud (renders nothing by
  default: `defender_ownership: platform`). Each Terraform call passed `terraform validate` and each
  Bicep call `bicep build` against the pinned module; no render, `terraform test`, ARM test or eval
  covers them and nothing is applied. Open from the writing: diagnostic category names are not
  checked against a live resource (each set says to check before a render); the Terraform modules of
  firewall, firewall policy, public IP, load balancer, Bastion, VM, disk, route table, SQL, PostgreSQL,
  MySQL, Static Web App, Container Instances and the key/secret submodules pin `azurerm` 4.x (a root
  calling them cannot be on 5.x), AKS, private endpoint, private DNS zone, NAT gateway and Managed
  Redis are AzAPI-only, and `avm.md`'s table does not list them yet; `privateDnsZones` got the
  abbreviation `pdnsz` in `naming.default.yaml` (it was empty - check the provider derives no zone
  name from it); `central_inspection` and `hub_gateway` (peering) are `platform` booleans missing
  from `deployment.yaml`; the `resource_lock` list leaves out managed disks; no new
  set has a diagram icon or layout. The four plugin descriptions were shortened 2026-10-26 (1,847
  to 1,477 characters, 74% of the 2,000 listing budget; the `iac-authoring` entry no longer
  repeats the handoff to the other skills), so the next family's terms fit in `azure-resources`.
- **State before that: 25 resource sets in 10 families**, all with both rendering references, both checks
  green: storage-account, blob-container, file-share, queue; virtual-network,
  network-security-group, application-gateway, front-door; app-service, function-app,
  container-apps, container-registry; cosmos-db; key-vault, user-assigned-identity;
  log-analytics-workspace, application-insights; foundry, search-service; service-bus,
  event-hubs, event-grid-topic (`messaging`); api-management (`integration`); backup-vault,
  recovery-services-vault (`recovery`). The deployment set has 38 questions; 562 in total.
  The eight sets added 2026-10-25 (messaging, integration, recovery, application-gateway,
  front-door) are checked, not exercised: every Terraform call in their `terraform.md` passes
  `terraform validate` against the pinned module version (module installed from the registry,
  variables stubbed), every Bicep call compiles with `bicep build` (parameters stubbed with
  `any()`); no example renders them, no eval covers them, nothing is applied.
- **First applied render (2026-10-25): `eval-agent/`**, Bicep, one stage, deployed through its
  own rendered GitHub pipeline (what-if, approval, deploy; OIDC). The first run fed three
  fixes back into `pipelines.github.md` and `check_pipeline.py` (job without checkout,
  partial what-if, immutable OIDC subject). Not yet in the plugin: the instance number in the unique-name seed. Terraform and the other pipelines have not run.
  Since 2026-10-25 the spec and the render (not yet deployed) split it in two: a public
  dashboard (sign-in, reads the results, holds the GitHub token) and an agent behind a private
  endpoint (runs plugin code, writes the results, no secret), on one B2 plan, one user-assigned
  identity each; the tests assert the separation (`ideas/eval-agent.md`). Decided 2026-10-25: the dashboard files a ticket on a click, never automatically; its image goes in through
  `.github/workflows/deploy.eval-agent.dashboard.yaml` (the pipeline opens the registry for the runner's address only and closes it in an
  `always()` step; `container-registry.networking.image_push_path`, needs AcrPush for the pipeline identity). The dashboard app is
  `eval-agent/dashboard/` (Node 22, Express; `MOCK=1` or `run-local.ps1` runs it without Azure; pages Overview and Tune & Fuzz; it starts
  the tuner only, the tuner starts the fuzz agent; reads `runs/`, `fuzz/`, `tune/` from the storage account; agents not written yet,
  `POST /run` and `tune/<id>/run.json` are its contract). Open there: the plugin source, models, the sign-in secret, the GitHub token
  `github-token`. The storage account's container `results` (prefixes `runs/`, `fuzz/`, `tune/`) is in the spec as `blob-container` and rendered. The old single identity `id-…-02` and, if the first
  render was deployed, its role assignments stay orphaned until deleted by hand.
  Since 2026-10-26 two more apps on the same plan, spec and render (not deployed): a fuzz agent
  (draws random specs with the plugin's diagram script, scores the layout, writes the report to
  storage; image and data role only, no vault, no model) and a tuner (timer in the app reads the
  newest fuzz report, lets the model draft a change to `new_diagram.py`, commits it to a tuning
  branch when the score drops and the tests pass, then starts the fuzz agent; it skips a run while
  the fuzz agent is going, never merges, never touches `master`). The timer runs every 24 hours (stage file). Open: `application.tune_commit_limit` (commits per run), `application.tune_github_token`. The fuzzer itself is `tools/diagram-fuzz/`, outside
  the plugin (development tooling, not shipped; `ideas/diagram-fuzz.md`). Its zone check
  never fires on its own specs yet - only the `four-apps-one-subnet` fixture test guards the
  rule that a call inside one container stays in it.
  **Since 2026-10-27 the agent app is gone** (spec, diagram, render, pipelines; not deployed):
  the evals run in GitHub Actions instead (`eval.plugin.yaml`), recorded on the `eval-history`
  branch, and the dashboard only shows - eval history per plugin version and model, read from
  that branch through the GitHub API without a token, plus the fuzz and tuner reports from
  storage. No run start, no tickets, no `github-token` in the vault; drift and tune run on
  their timers only. Why: an always-on site and a private endpoint for a job that runs a few
  times a week, in a test subscription. The stage workflow's linuxFxVersion step had mapped
  drift, fuzz and tune onto the dashboard's parameter; it maps per site now.
- **Names before the deploy** (2026-10-25): `list_names.py` derives every resource's name
  from the spec and the convention, offline - no plan, no tool, no login is assumed; the
  render's step 8 hands the table over and asks "Passen die Namen?". `<UNIQUE_ID_n>` prints
  as `????`, global names are never reported free, private endpoints are not listed yet.
  `foundry`/`search-service` in `examples/chatbot` are named `${workload}foundry` by hand,
  the convention would give `aif-prod-chatbot-????`: one of the two is the rule.
- **Six examples, Terraform only, nothing applied** (release 0.3.0 is out, 2026-10-26).
  Rendered in full: `chat-sandbox` (the first full run with a customer and both agent
  loops, authored, 118 decisions, 32 tests), `chatbot` (per-family AVM, 284 decisions, 79
  asserted / 205 not-testable), `chatbot-rag` (authored, three stages, GitHub pipeline, 151
  decisions, 14 open) and `order-platform` (2026-10-26: AVM, seven family modules plus a
  wiring test and the GitHub pipeline, laid out as a customer repository, 23 resources, 63
  decisions all covered, 6 open). Spec, diagram and decision document only:
  `orders-integration` and `chatbot-multi-rg`. No example is rendered in Bicep.
- **Checks:** `check_repo_consistency.py`, `check_question_set.py`, `check_spec.py`,
  `check_render_coverage.py`, `check_pipeline.py` (+ 55 cases), `run_arm_tests.py`,
  `run_diagram_tests.py`, `run_png_tests.py`, `verify_diagram.py`, `drawio_png.py`.
- **Eval baseline** (`evals/baseline.json`, 2026-10-18, $5.44): the dropped cases and
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
- **The diagram has a chain layout** (2026-10-25, from `examples/orders-integration`, owner's
  pictures to copy): three or more subnets of compute that call each other - gateway, API
  management, function - stand as columns in the order of `wiring.access`, the private
  endpoints the last, the line between neighbours straight. Actors that start a request
  (users, Front Door) are zones of their own left of the network at the row's height, one that
  is only called (Entra ID) a zone above its caller; identities, monitoring and name
  resolution stand in a column under them, security groups and identities of one kind as one
  icon. Calls into services leave the bottom of the subnet along a lane; a call from a
  service into compute (Event Grid delivering to a function) is a word on the function, no
  line. No frame around everything, with or without a resource group split. Private DNS
  zones with nobody named for them are drawn red and *open*, not left out. Not done: the
  PaaS-to-PaaS lines along the strip above a compact row are still the noisiest part.
- **Every diagram carries an AI notice** (2026-10-25, owner's call): a yellow badge with a
  robot on the title row, right of the title (`KI-generiert - bitte prüfen` /
  `AI-generated - please review`, by `context.language`). `new_diagram.py` draws it in every
  render and `run_diagram_tests.py` fails without the `ai-notice` cell. The six rendered
  pictures (`examples/*`, `eval-agent/infra`) got the cell by hand in the existing XML, not a
  re-render, so the signed-off layout stays; the four `docs/` pictures likewise (German text,
  no generator behind them).
- `docs/process.drawio.png` and `docs/process-agents.drawio.png` show the flow of
  2026-10-24, `docs/skills.drawio.png` the skills, the entry and how the units relate
  (generator in the owner's `drawio-diagrams` skill style; the PNG is the source). The
  process pair was rendered headless in a cloud session and wants one open in draw.io on
  the owner's machine to confirm it still edits.

## Road to 1.0.0

1.0.0 means stable formats (owner's call, 2026-10-29): the spec format and the question-set
format are frozen - a breaking change waits for 2.0, an older customer spec keeps working
through `plugin_version` and the version gate - the known customer-facing faults are fixed,
composition is proven by a pattern skill, and Terraform has been applied once. Full coverage
of the 67 resources is not part of it; it continues in 1.x.

Must:
- **Freeze the formats.** Merge the format revision (#15), then name in `spec.md` and
  `question-set-format.md` what is the stable interface, and how a spec from an older plugin
  is carried forward.
- **The pattern skill** (`ideas/pattern-skill.md`): `patterns/` is empty; composition is
  proven by two hand-wired examples only.
- ~~**A Terraform render applied** through one rendered pipeline, as `eval-agent/` did for Bicep~~
  - done (owner, 2026-10-29).
- ~~**The decision document prints raw values**~~ - done (2026-10-29). Every question has a
  `plain`; the raw values came from spec keys the sets do not have (`orders-integration`
  had ~30). `check_spec.py` now fails on a resource key that is no question of its set or
  sits in another group; `orders-integration`, `order-platform` and `eval-agent` were moved
  onto the sets, which gained `storage-account.hierarchical_namespace`,
  `virtual-machine.instance_count`, `app-service.container_image_owner`, `entra_sign_in`,
  `entra_client_secret` and `container-registry.image_push_path`. Nested list entries read
  as words, not Python. In `order-platform` only the `# decision:` names were renamed; in
  `eval-agent` the Bicep still calls the sign-in hand-rendered.
- ~~**A public app "without a filter" has no sign-in** (see *Interview and spec*)~~ - done
  (2026-10-29): the option no longer promises a sign-in, it notes that the application decides.
- ~~**`check_spec.py` does not check enum values**~~ - done (2026-10-29): an enum value, or a
  list item where `accepts` is a list, outside its question's `accepts` fails, per stage;
  unknown keys in `wiring.access` fail too.
- ~~**Phase 4 shown as text before "Passt das Design?"**, confirmed in a fresh interview~~ -
  done (owner, 2026-10-29, tested in another repository).
- ~~**The suite runs green on Sonnet** before the release~~ - done for 0.6.0 (2026-10-29):
  11/11, composed with a re-test of `diagram-no-invented-lines` after a grader fix (see *Evals*).
  Holds for every release from here on, not once.

Should:
- The AVM version drift check (`ideas/avm-drift-watch.md`).
- The former `confirm_in` defaults wired to requirements; the savings concept.
- The naming revision (owner's todo).
- The diagram generator faults listed under *Diagram generator*.

After 1.0: rendering and testing the 42 resources checked only against their modules, the
cross-backend diff of one spec, the remaining resources, "engineer" in the resource sets.

## Open

Grouped by where the fix lands. A module's README on `main` is ahead of its tag: Event Grid topic
(`parent_id`, `input_schema`) and Application Gateway (`parent_id`, no public IP input) were
first written from `main` and failed `terraform validate` on the pinned tag. Write and check
a reference against the installed module, never against `main`. Each item is a finding from a run or a review, kept
until it is fixed or decided against.
- **The examples still carry `system_assigned` for Foundry, storage account and AI Services** (chat-sandbox, chatbot, chatbot-multi-rg, chatbot-rag): their specs, renders and tests predate the `none` default. Re-render them or leave them as the explicit value; either is valid, but a fresh interview now answers `none`. The Foundry project child keeps its own system-assigned identity (the API requires it); SQL database, search and API Management were left at `system_assigned` on purpose - their roles and data sources need it.

- **Canonical spec** (2026-10-26): every tracked `infra-spec.yaml` (six examples,
  `eval-agent/infra`, six pipeline fixtures) is laid out with `write_spec.py --no-stamp`;
  every spec reader gave the same result before and after (`export_decisions.py` and
  `check_render_coverage.py` in a new order only), and the example and eval-agent decision
  documents were re-exported. `check_repo_consistency.py` fails on a tracked spec that is
  not laid out. Open: the `requirements-stated` graders `canonical-requirements-group` and
  `canonical-no-anchors` are load-checked, not run - a run without a shell lays the form out
  by hand, and whether it does is unmeasured. The diagram and spec-test fixtures are not
  named `infra-spec.yaml` and not laid out; `run_spec_tests.py` edits its fixture as text.

### The sources behind `render-map.yaml`

Done on `render-yaml`: `renders` dropped, the self-contradicting references corrected, the
decision tables removed, the design gaps closed, the inherited deployment answers translated
(`answer: { deployment, map }`, 54 questions, required where the values differ), and the gaps
filled from primary sources - 969 to 513 (18% to 9% of 5,216 entries): the azurerm 5.12
schema and docs, the module READMEs at the documented versions, `bicep build` for paths. Each
fill names its source in its note; the pass also corrected eight entries the sources
contradicted. Left:

- **The remaining 513 gaps.** About 160 are permanent: the Bicep resource-group scope,
  inputs a module README shows it does not have. The rest: Bicep literals of loosely typed
  properties - `bicep build` proves the path, not the value, where the type is `string` or
  `'A' | 'B' | string` (diagnostic `AllMetrics`, `linuxFxVersion`, `activeRevisionsMode`) - and
  shapes no source states (Windows image literals, policy schedules, NSG baseline rules, the
  question-less app setting names). A live deployment or the ARM REST specs would settle the
  loose literals; neither is a source this pass used.
- **API versions the authored Bicep was proven against** are named in each note; most
  `bicep.md` files name none for their sibling types (diagnostic settings, role assignments,
  private endpoints). Writing them into the references is open.
- **Prose that may be outdated**: ai-services, foundry and api-management say the Bicep module
  has no `allowedFqdnList`; README 0.19.1 has it (the maps are filled, terraform.md and
  questions.yaml are not). event-grid-namespace renders the namespace with azapi although
  azurerm 5.12 has `azurerm_eventgrid_namespace`. cosmos-db's note that the Terraform module
  refuses `AllMetrics` is not in its README - only its source would show it.

### Rendering references and question sets

Done 2026-10-25: the azurerm 5.x spellings (checked against `terraform providers schema -json` of
5.11 and the provider docs at the tag; only storage has the string `public_network_access`), the
module `diagnostic_settings` interface (two forms, see `avm.md`), every diagnostic category name
(compared with Microsoft Learn's supported-categories pages; Backup vault has no
`AddonAzureBackupAlerts`), the Function App delegation (Flex `Microsoft.App/environments`, Elastic
Premium `Microsoft.Web/serverFarms`), the Foundry project API version, `foundry.allowed_fqdns`,
`storage-account.private_endpoint_subresources.depends_on`, the sets `backup-vault`,
`recovery-services-vault`, `blob-container`, `file-share`, `queue`, `deployment.resource_lock`, the
`app-service` `plan` decision (own or shared), the Bicep per-family shape, `granularity:
per-family` in `check_spec.py` and the `chatbot` spec, and `references/private-dns-zones.md`.

- **Revise `naming.yaml` and the naming** (2026-10-27, owner's todo): the convention
  (`core/iac-rendering/references/naming.default.yaml`) and the naming interface
  (`references/naming.md`) get a rework; the scope is the owner's to set before a session
  starts on it. It came up with the Foundry region departure: the account's pattern carries
  no `<LOCATION>` while most others do.
- **Foundry in another region is not rendered anywhere yet** (2026-10-27): `check_spec.py` and
  `run_spec_tests.py` cover the spec side, `terraform.md`/`bicep.md` the shape; no example, eval
  case or `terraform test` exercises `foundry_location` and the endpoint on `var.location`.
  Under `data_zone` the departing region is not machine-checked against the zone - the same
  region table the pipeline guard below needs would close it.
- **Pipeline guard for `location` against `data_residency`**: not done. It needs a region -> country
  and data-zone table (`az account list-locations` carries `geographyGroup` and `geography`), an
  invariant 13 in `pipelines.md`, a step in the four platform files and the local script, a check
  in `check_pipeline.py` and a mutation per platform, and the six fixtures under
  `tests/pipelines/` rebuilt.
- **The sets from 2026-10-23 have no Bicep render** (`chatbot` is Terraform only) and
  `*.armtest.yaml` is still one file per example; the per-family Bicep shape is documented and the
  nested path checked on a toy compile, not on a render.
- Missing sets: Container Apps session pools; a Table storage set; Event Grid domain. The gap review of
  2026-10-25 lists what is still pending (no question set yet; the high-priority batch was written
  2026-10-25 and the first half of the Medium list 2026-10-26, see State):
  - **Medium, still open:** network: Virtual WAN / VPN Gateway / ExpressRoute, Private Link Service;
    data: Synapse, Databricks, Data Explorer, Fabric Capacity; observability: Diagnostic Settings as a
    resource of its own, Managed Grafana, Azure Monitor Workspace (Prometheus), Dashboards; messaging:
    Notification Hubs, SignalR / Web PubSub; governance (the family itself is parked in `drafts/`): Budgets, a standalone lock,
    Automation Account, Maintenance Configuration (resource groups stay a deployment decision).
  - **Low:** storage: Table, Managed HSM, NetApp Files, Files Sync, Data Lake Gen2 as its own type;
    compute: Batch, Service Fabric, App Service Environment, Spring Apps, Compute Gallery, Dedicated
    Host, Virtual Desktop, Arc; security: Managed HSM, Sentinel, Confidential Ledger; data: Cosmos DB
    for PostgreSQL, Time Series Insights, SQL VM; IoT Hub, DPS, Digital Twins; Maps, Load Testing,
    DevCenter, Dev Box.
- A container's throughput in Cosmos DB is one value for all; the NSG baseline rules per
  `subnet_purpose` are general knowledge, to be confirmed per service before a render; the Key Vault modules'
  `keys` member names are read from the README at render time.
- New sets, known gaps in the modules: Service Bus (the Terraform module refuses
  `DiagnosticErrorLogs`; no input for zone redundancy or geo recovery), Event Hubs (no Terraform
  input for TLS minimum, double encryption, zone redundancy, consumer groups, geo pairing; the
  README calls `network_rulesets` Premium-only, check), Backup vault (the Bicep module has no
  diagnostics or Resource Guard parameter), Recovery Services vault (the Terraform module has no
  soft-delete retention input), Front Door (the policy and the security policy bind by hand),
  API Management (v2 tiers: which of private endpoint, VNet injection, VNet integration each
  supports is read from the documentation before a render). `DELEGATIONS['function-app']` in
  `new_diagram.py` is Elastic Premium's; a Flex app is drawn with the wrong delegation.
- Diagram: the new kinds have icons (`ICONS`) and a resource group role, but no layout of their
  own; Application Gateway, Front Door and API Management are drawn as services, not as the edge
  in front of the compute.
- `app-service` with `plan: shared`: the render documents are written, no example renders it, and
  the `<?SUBNAME>` / second private endpoint naming is untested.
- Evals: none for the new sets, for `resource_lock`, or for the shared plan.
- **Secret placeholders in Bicep are `@onlyIfNotExists()` by default** (the pipeline runs the latest Bicep; a local `az bicep` may reject it).
  `key-vault/bicep.md` and the security routing say so; the case `render/bicep-secret-placeholder-once` grades it (load-checked, not run).
  `eval-agent/infra` is moved (2026-10-25): `vault.bicep` has the decorator, `main.bicep` no `existingSecretNames`, the lookup step
  is gone from `eval-agent-infra-stage.yaml`, the tests assert that no lookup condition or parameter is left (`absent`). Not
  verified: a local `az bicep` rejects the decorator (BCP057), so the compiled ARM and those tests have not run against it;
  the first pipeline run (`az bicep build` on the runner) is the check, and how the decorator shows in the ARM is still unread.
- **A re-render of `eval-agent/infra` from the spec (2026-10-25) reproduced the hand-written Bicep** except one property
  (`keyVaultReferenceIdentity` on the fuzz app, which has no vault access; removed). The re-render was not independent: the
  renderer read the old modules first. What the plugin does not carry, so a render from the spec alone would guess:
  - app settings (`STORAGE_ACCOUNT_NAME`, `FOUNDRY_ENDPOINT`, `GITHUB_TOKEN` as a vault reference, schedules, a peer's hostname)
    appear in no spec and no reference; the spec needs a place for them (a decision per setting, or a `wiring` entry);
  - the authored section of `resources/compute/app-service/bicep.md` shows the AVM call only: a container site, user-assigned
    identity with `acrUseManagedIdentityCreds`, `keyVaultReferenceIdentity`, `WEBSITE_PULL_IMAGE_OVER_VNET`, a private endpoint
    with zone group for a site, `authsettingsV2` and the `existing...LinuxFxVersion` pattern for `container_image_owner:
    image_pipeline` are missing;
  - several sites on one authored plan: the shared-plan section covers the AVM module only;
  - `run_arm_tests.py` and the other scripts are run with `python -I`; the skills do not say so.

### Interview and spec

- **Wire the former `confirm_in` defaults to requirements** (2026-10-28): `confirm_in` was
  removed - a marker in a document nobody reads changes nothing. Defaults the customer can
  judge get a `derived_from` instead: `outage_impact` → `compute_tier`/`service_tier` (SQL,
  MySQL, PostgreSQL), the Service Bus and Event Hubs `sku`, Redis `sku_name`;
  `expected_load` → VM/VMSS `size`, Search `sku`, Cosmos `capacity_mode`, Event Grid
  namespace `capacity`; `priority: protection` → AKS `defender_enabled`, SQL MI
  `vulnerability_assessment`, VNet `ddos_protection`, DDoS `stages_with_plan`, Firewall
  `sku_tier`/`idps_mode`/`threat_intelligence_mode`. Each with a map and the guardrail check.
- **Revise the savings concept as a whole** (owner's todo, 2026-10-28):
  `deployment.non_production_savings` and the per-question `non_production_default` (72
  questions, about 60 of them beside a `derived_from`, the rest beside a `default`). The
  name is unwieldy and the field reads like a second default; folding it into `default`
  does not work, since most of these questions have none and one answer path is the rule.
  Look at it together with `priority: cost`, which equals `balanced` for every knob wired
  so far.
- **`forced_when` stays prose** (2026-10-28): of its 211 uses about 60 are a single
  condition and perhaps 30-40 a plain "X = A forces B"; the rest carry minimums, removed
  options, several conditions or facts no set holds (a paired region in another country) - a
  schema for a fifth of them would be a second mechanism, not a simpler one. What is
  checked: `check_spec.py` resolves a `forced_by` key against the spec and the sets.
- **`allLogs` on request only** (guardrails §5, owner's call 2026-10-29): audit categories
  always, `allLogs` only when a mandate or `priority: protection` asks - the guardrail says
  so now; the sets do not yet. Derive the category questions from `priority` (as change feed
  and flow logs already are) and name the mandate case. Outside production, give
  `daily_quota_gb` a `non_production_default` (its default is `-1`, no cap) - part of the
  savings revision.
- **Phase 4 lists an exception from an earlier spec again** (guardrails §6, 2026-10-29): the
  rule is written; whether a carried `overridden` value reaches the sign-off and the decision
  document's "decided differently" section is not verified.
- **"engineer" in the resource sets** (2026-10-28): removed from `core/`, still in 19
  question sets under `resources/` (`why` texts, e.g. communication-services
  `data_location`). There is no engineer role; rephrase.
- **Every list question's `plain` ends in "(empty: none)"**, also when the list is not empty
  ("Queues: payments (…) (leer: keine)"). Seen 2026-10-29 in `orders-integration`; the
  wording of the sets, or the decision document drops the clause for a non-empty value.

- **A chat-app test with a slot as the test stage** (2026-10-27, 0.5.4) left: Phase 0 asks two
  points in prose (what for, who from where) and announces no default; stages and every
  fixed-answer requirement are the batch's. `public_parts` is forced when one application is
  the only part people open. Deployment slots are a `slots` group of the App Service set
  (`slot_access` interview; slots force Premium v3 and one shared user-assigned identity),
  and Phase 4 says a slot named as a stage runs on production data. The sets are read
  through `interview_digest.py` (a run's own extraction dropped `forced_when`). The diagram
  is shown as a draft first (draft question: are the parts and connections right?); Loop 1
  polishes only a confirmed draft, and the code question follows the polish. Open: whether
  Phase 4's "Passt das Design?" and the draft question confirm the same thing twice;
  `docs/process.drawio.png` still shows the review before the customer. Open: no
  render, example or eval case with a slot; an `open:` entry may still name a resource the
  spec does not have (proposed: a `check_spec.py` rule); `offer` texts repeat the value
  their label already shows (`30 Tage - ...`); whether the progress line before each batch
  call stays at all; the eval suite has not run on this branch.
- **Deployer roles are in the spec** (2026-10-26): `deployment.deployer_roles`, derived
  (`forced`), lists what the deploying identity needs beyond `Contributor` - `Contributor` on
  `subscription` for a `create` group, `Role Based Access Control Administrator` for any role
  assignment, `Key Vault Secrets Officer` per vault with placeholders. `check_spec.py` fails on
  a missing one and warns on a spec without the key; `run_spec_tests.py` breaks each; the
  hand-over in `pipelines.md` names them. Every example spec and `eval-agent/infra` carries
  it, derived by the rules and re-exported; the six pipeline fixtures under `tests/pipelines/`
  do not. Open: no rendered pipeline header lists the roles, and `check_pipeline.py` does not
  check the header against the spec.
- **`stage_isolation` is asked** (2026-10-26), with a landing zone too (customers keep a
  workload's stages in one vended subscription). `resource_group` forces every group to
  `existing` and the person is told that each stage's identity holds roles on its own groups
  only - a subscription assignment removes the separation; `check_spec.py` fails on a
  `create` group or a `subscription`-scoped deployer role under it. Open: no example and no
  eval case uses `resource_group`, and no pipeline render has scoped identities to groups.
  The consequence is confirmed through its own `AskUserQuestion` call with the way back.
- **Resource groups: whether, then how** (2026-10-26, from two test interviews with the owner as
  customer): `resource_group_layout` (single / split) and `resource_group_scheme` (concern,
  lifecycle - foundation, state, runtime -, protection - protected, standard -, component - shared
  and the parts the run names in `resource_group_components`) are asked (one group per resource type was tried and
  dropped: fourteen groups for a chat app, owned and deleted by nobody as a unit); `resource_group_split` is
  derived from the scheme's table and the design, corrected at the diagram sign-off. One reader,
  `iac-rendering/scripts/rg_roles.py`, for check_spec, diagram and decision document (`list_names.py` reads the split from the spec itself).
  `resource_groups_created` offers one option per group. Also from the interviews: `private` with `network_requirements: free` and users is a
  contradiction in the list. **A split has no main group**: every set has a role in both tables
  (or is `attached`), and Bicep renders one root per stage deployed into the first group of the
  split, modules scoped per group, references as module outputs - ordering whole groups ran into
  circles that do not exist between resources. The three tracked specs with a split predate
  `resource_group_layout` and keep their main group (a warning). Open: no render, no diagram
  fixture and no eval case for the new schemes (checked end to end on a copy of `chatbot` only).
- **The interview, as five test rounds with the owner left it** (2026-10-26/27): Phase 0 asks
  target, module choice and `deployment_scope` (resource group / subscription), then naming for
  Terraform; `stage_isolation` is derived from the scope, never asked. `app_runtime` (and
  `app_containers` for a container) is asked before any compute set is chosen - code on App
  Service, several containers on Container Apps, never Container Apps unasked. Every public app
  gets `public_audience` with three fixed options, `waf` recommended; `public_entry` is Front Door
  unless an Application Gateway is named. The address range is the last question, sized from the
  subnets (/25 for an app and its endpoints). Options come from the question set (`values`, the
  new `offer` field), an empty multi-select answer is an explicit option, "Other" is read, never
  guessed. `check_spec.py` fails on a role granted to a resource the spec does not have. Open:
  the container-apps set is one environment with one app, so two apps (a chat front end and an
  import worker) render two environments and two subnets - it needs several apps per
  environment; `central_backup` is asked before `backup_isolation` and so also when no copy
  leaves the system; the round-5 spec and diagram live in a scratchpad only.
- The diagrams of `chatbot-rag`, `chat-sandbox` and `orders-integration` were not redrawn
  after region/subscription became `open:` (2026-10-26); `chat-sandbox`'s carries hand edits
  a redraw would lose.
- `wiring:` is validated by example only. (`check_spec.py` knows `granularity: per-family`
  since 2026-10-25 and the `chatbot` spec declares its seven family modules.)
- `export_decisions.py` prints `reason` and `open:` texts untranslated. `infra-decisions.docx` is missing everywhere (no `pandoc`).
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
  - **Deployment scope is asked** (2026-10-26): `deployment_scope` (`resource_group` /
    `subscription`) before the group questions; `resource_group` keeps every group `existing`,
    `subscription` deploys with `az deployment sub` and `--location` and needs Contributor on the
    subscription (`deployer_roles`). Invariant 13 in `pipelines.md`, every platform file names the
    swap, `check_pipeline.py` fails on a command at the wrong scope (two mutations). Open: no
    fixture renders a subscription-scope Bicep pipeline end to end.
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
    through review and diagram agents; `new_diagram.py` was not touched in the loop). A second
    run the same day (review, hand fix, second pass per example) ended with no error in any of
    the four; what is left is `polish`: the telemetry line of `chatbot` and `chatbot-multi-rg`
    runs 7-8px beside the Monitoring frame, "HTTPS 443" and "sign-in" sit close above their
    lines, the `chat-sandbox` app-service exits are 19px apart. The `chatbot` decisions panel
    prints the German `deployment.mandates.value` in an English picture: the value is the
    spec's, change it there. The hand edits of
    `chatbot-rag`, `chat-sandbox` and `chatbot-multi-rg` live only in the PNGs; a regeneration from
    the spec loses them. Script faults behind the findings:
    - a target below the zones is reached by a detour through the private endpoints' trunk (or,
      when hand-routed, through another zone) - the corridor belongs left of the trunk;
    - edge labels sit in the middle of a line and land on frame borders - offset them, or move
      them onto a drop outside the frames;
    - actor lines on one side of a target and every top-to-top edge share one track;
    - the slot order ignores which services call each other, so lines cross (sort by edge
      adjacency, stagger actor lines by the target's height);
    - with three or more callers the entries into the private endpoints' icon are 9-10px apart
      (`entryY` 0.2-0.8) and two edges from one source leave at the same `exitY`, so they run
      collinear: spread entries over the icon's sides, top and bottom from the third caller;
    - the Monitoring zone title reads "Monitoring · monitoring (created)" with a split - name the
      group once;
    - the legend has no entry for purple role text or the orange public-access warning, and the
      decisions panel prints raw spec values ("Netzwerk: none", "Private DNS: deployment");
    - the legend line "existing, not created here" next to a dashed network group frame reads as
      "this run builds none of it" although the group exists and its contents are created.

### Pipelines

- The pwsh pipelines have parsed and been dry-run with a mocked `az`, never run on a
  runner: the next push of `eval-agent/infra` to `dev` is the first real run of
  `eval-agent-infra*.yaml` in pwsh; the ADO and GitHub Terraform fixtures have not run at all.
- An `open:` entry without `environments` allows a placeholder in every stage file and
  requires none (`check_pipeline.py`): it may be a per-stage value (`context.location`) or
  none at all (a model list). The runs no longer need to name the stage as a workaround.
- GitLab has no scaffold behind it and is untested; Azure DevOps and GitLab accepting their
  file was never checked. The Terraform pin is `~> 1.17.0` (ADO `1.17.1`, GitLab image
  `1.17`), resolved on 2026-11-01.
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

- **Evals before a merge, none on the pull request (2026-10-27)**: the full suite runs on Sonnet
  (low effort, ~$12-18) before a merge, locally (git-commit-conventions, section 5); each case
  runs its own `runs:`, 4, and 2 for the four costing $3+ on Sonnet (owner's call, 2026-10-27:
  cost over resolution, those read only 0/50/100%), no `--runs` flag;
  Haiku runs beside it every time (owner's call, ~$1-3) as the floor - reported, compared only
  with earlier Haiku runs, never blocking a merge on its own;
  `eval.plugin.yaml` runs it by hand on Linux. The PR run on Haiku was removed: it measured
  the model. First CI run on Haiku, 13 cases: 23:45 min,
  $2.18, 2/13 at 100%, 0% on every process, sync and render case - Haiku skips multi-step rules.
  `language-de-request` and `module-source-authored` removed (100% on Opus and Haiku).
  `iac-authoring/SKILL.md` is ~11,400 words, loaded on every run: the hard rules (no code before
  the sign-off, invent nothing, the default stack) are spread through it - a candidate for a
  short rule block at the top.
- **Sonnet, full suite (2026-10-27, local, effort low)**: 6:17 min with 8 runs in parallel,
  $17.43, 5/11 at 100% - every spec case green. 0% on diagram-before-code-after-change,
  review-agent-separate and claude-md-section-replaced: all three ran without a shell (no Bash
  in the Windows sandbox) and dropped a rule buried in `iac-authoring` (sign-off without a
  picture, the CLAUDE.md sync by hand, the stamp); a rule block at the top of the skill and a
  "Without a shell" section answer it, not re-measured yet. Those cases measure the plugin
  only with a shell: on a Linux runner with Bash granted.
- **0.6.0 before the merge of #15 (2026-10-29, local, effort low)**: full run on `2ddb25d`,
  Sonnet $15.62 10/11, Haiku $1.69 6/11. The one Sonnet failure, `diagram-no-invented-lines` /
  `no-invented-calls` (0/2, REGRESS against 3/3), was the grader: it matched the derived
  `Monitoring Metrics Publisher` from the app on Application Insights that
  `application_monitoring` adds since 0.5.6. Fixed in `07f1aa0` (entry in `LEARNINGS.md`);
  re-test Sonnet 2/2, Haiku 0/2 (real invented lines and purposes, 8-11 turns, not chased).
  Recorded on `eval-history` as 0.6.0 (`ffbb421`), composed, the badge pinned to it.
  The composed Sonnet run is `baseline.json` since (owner's call): 11 cases, every grader at
  its full rate. Haiku keeps failing the same rules as on 0.5.4/0.5.5: invented subscription and
  region, the default stack, `@onlyIfNotExists()`, the CLAUDE.md sync in one of four runs.
- **0.7.0 (2026-11-01)**: Sonnet 14/14, recorded on `eval-history` as `8e1bd6c`, composed - the
  full suite on `a4cf3c2`, the `terraform-*` cases re-tested after #26 (graders read file
  contents), `terraform-code-structure` after #27; the badge pinned to it (#29). New since
  0.6.0: `spec/platform-workspace-reference` (the interview writes `{ existing:
  log_analytics_workspace }` with an open id) and `render/terraform-existing-reference` (id
  variable validated on the ARM type, the id per stage file, no data source) - every render
  case now runs through the mandatory render digest, though no grader asserts it was read.
  `baseline.json` is still the 0.6.0 run (11 cases).
- **CI by hand**: `.github/workflows/eval.plugin.yaml` (`workflow_dispatch`, Sonnet/low by
  default, one case per call with progress, `--scaffold`, report only);
  `record_eval_history.py` writes each run to `eval-history`. `review-agent-separate` never loaded before 2026-10-27 (`focus:
  transcript` is not a value; `trace` is). It needs the secret `ANTHROPIC_API_KEY`. Unverified on a Linux runner: whether the eval
  sandbox needs bubblewrap there although no case grants a shell. Haiku has no baseline
  yet; its rates are compared with Haiku's own, never with `baseline.json`.
- `render/app-code-untouched` (2026-10-27): a signed-off Key Vault spec beside a .NET app
  whose configuration key does not match the render; no Write/Edit on app files, the
  mismatch named in the hand-over. A C# fixture without credential calls, not JavaScript:
  the Claude plugin scanner complains about a `.js` file in the plugin directory. First
  measured in the run before the 0.5.3 merge.
- Triggering is covered by `trigger/trigger-workload-request` ("eine Chatapp in Azure mit
  RAG", no resource named, must open the interview); it passes.
- No grader checks `implementation` or `module_source`. No case for: the delivery
  questions; an engineer-flavoured request asserting no `engineer` question is asked;
  the whole `requirements` group reaching the customer (the gap of 2026-10-24); the
  customer-question graders (question count, Azure vocabulary in the questions,
  readability).
- `vague-public-dev` at 78%: both causes are plugin rules written after the baseline. The
  next full run (~$5) should lift it; accept with `--update-baseline` after reading it. Its
  `context-not-opened` grader became `open-location`/`-subscription`/`-resource-group` and
  `no-invented-location` (2026-10-26), not yet run; the baseline still names the old one.
- The plugin-vs-plain pilot needs 3 runs per arm and cases on the small decisions
  (replication, soft delete, infrastructure encryption, SFTP), ~$15-25, before it counts.
  `terraform validate` in an eval needs a Linux runner; the spec-graded cases cannot run
  without the plugin.

### Landing-zone interview (2026-10-26)

- `backup-vault` and `recovery-services-vault` always render their own vault; the
  `backup_ownership: reference` case is not rendered yet.
- `container_image` is still an `open:` entry; `central_private_dns`' text promises an open
  zone location that `private_dns_records: policy` does not need.
- No case for the sandbox path, `landing_zone_exists: yes` with the new exposure question, or
  `public_parts` mapping a download area to a storage account. The `expected_load` maps
  (App Service P1v3/P2v3/P3v3, SQL 2/4/8 vCores) are estimates, not measurements.
- The contradiction list in `iac-authoring` is a skill rule, not a script check.
- Idea: a cost estimate in Phase 4 (`ideas/cost-and-security-profiles.md`).
- `examples/order-platform` was deleted (2026-10-29, owner's call): it predated the spec
  revision and was to be regenerated anyway. It was the only per-family and pipeline render;
  `chat-sandbox` is now the rendered example the `CLAUDE.md` commands test.

### After the spec revision (2026-10-29)

- `chatbot-multi-rg` and `orders-integration` were moved to a full split (no main group):
  the roles that lived in main (`security`, and `application` in `orders-integration`) are
  groups of their own now. `chatbot-multi-rg`'s diagram and decision document were
  regenerated with the Application Insights change (2026-10-29); `orders-integration`'s and
  the other examples' `infra-decisions.md` are still behind their specs - regenerate them.
- `.github/workflows/eval-agent-infra-stage.yaml` and `examples/chat-sandbox/deploy.ps1` are
  rendered with the old guard line (no `ASSUMED:`); neither spec assumes anything, the next
  render brings the line.
- The six pipeline fixtures (`core/iac-rendering/tests/pipelines/*/infra-spec.yaml`) carry no
  `schema_version`, so `check_spec.py` fails on them; `check_pipeline.py` does not mind.
- `wiring.private_dns_zones` stays in `wiring` (a zone serves an endpoint kind, not one
  resource); it duplicates `private-dns-zone.zone.zone_names` when the deployment owns the
  zones, and its `forced_by: deployment.network_exposure` is loose. Left until it diverges.

### Waiting on the owner

- A sandbox subscription with a federated credential and a fenced resource group for the
  deploy agent (`ideas/autonomous-terraform-agent.md`). The first apply ran in the owner's
  own subscription (`eval-agent/`); a fenced sandbox is still missing.
- `patterns/` is empty: composition is specified and proven by two hand-wired examples
  only (`ideas/pattern-skill.md`).
- An AVM version drift check, read-only, scheduled (`ideas/avm-drift-watch.md`).
- First run of the image pipeline (AcrPush is granted, 2026-10-25) and a check that its closing step really leaves the registry at `Disabled`. The dashboard's real mode (blob, GitHub, sign-in) has not run.
- The repository secret `ANTHROPIC_API_KEY` for `eval.plugin.yaml`.
- A first manual run of `refresh.foundry-models.yaml` after the merge: whether the `production`
  identity (Contributor on its resource group) may read the model catalogue at subscription
  scope, else Reader on the subscription; and "Allow GitHub Actions to create and approve
  pull requests" switched on.
- If the agent site was ever deployed: delete by hand what the incremental Bicep deploy leaves
  behind - the site `app-…-evalagent-agent-02`, its identity, private endpoint and role
  assignments, and the vault secret `github-token`.

### Environment

- A cloud session needs `registry.terraform.io`, `releases.hashicorp.com`, `github.com`
  release downloads and `mcr.microsoft.com`, and installs `terraform` and `bicep` into
  `~/.local/bin` itself. No Linux in WSL on the owner's machine.

## Next

**Regenerate the remaining examples and freeze the formats** (*Road to 1.0.0*): `render-yaml`
(#22) is in `dev`, rendered and graded with structured references in the 0.7.0 run (see
*Evals*). The examples go against the revised spec first, then `spec.md`,
`question-set-format.md` and the render-map format name their stable interface. What is
left of the sources (*Open*) is small and can follow.

**The pattern skill** (`ideas/pattern-skill.md`, draft PR #16): the wiring that `chatbot` and
`chatbot-rag` carry by hand — roles between resources, the private link, the order
identity → vault → consumer — becomes the first pattern, `./patterns/` enters
`plugin.json` in the same commit, and `wiring:` becomes a schema `check_spec.py` validates.
Before it, the eval case that asserts the `requirements` group reaches the customer (the
`backup-vault` set it waited for exists since 2026-10-25). Beside it, when a
run is paid for anyway: the eval suite re-run against the rules written after the
baseline, and `agents.md`'s two missing rules. The chatbot case in Bicep is what tests the
sets from 2026-10-23 cross-backend; it follows the pattern, not the other way round.
