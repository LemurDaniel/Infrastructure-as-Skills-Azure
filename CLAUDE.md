# CLAUDE.md

Guidance for Claude Code when working in this repository. `PROGRESS.md` holds the state
between sessions — read it first, rewrite it last. `README.md` holds the pitch and the
status; neither is repeated here.

## What This Repo Is

A Claude Code **plugin** that authors Azure infrastructure as Terraform or Bicep. Not a
module library and not a template collection: the knowledge is shaped as **question sets** —
the decisions a resource forces, in YAML, each with the reasoning that justifies its default
and the attribute it renders to. A storage account is not hard because the HCL is hard; it
carries about forty decisions, and generic generation gets the syntax right and the
decisions wrong.

The decisions render **to Azure Verified Modules (AVM) first** — a resource with an
`Available` module in the [Terraform](https://azure.github.io/Azure-Verified-Modules/indexes/terraform/)
or [Bicep](https://azure.github.io/Azure-Verified-Modules/indexes/bicep/) index becomes a
call to it with every decision as an explicit input; authored resources are the fallback
for a type without one, or for a repository that already renders that way. The contract
is `core/iac-rendering/references/avm.md`.

| Layer | Role |
|---|---|
| **Resource families** (`resources/<family>/`) | Reference material, not skills. One directory per resource, its decisions in `<resource>/questions.yaml`; the `azure-resources` skill routes into them |
| **Pattern skills** (`patterns/`) | Pre-answer most of a resource's questions and own the wiring between the parts |
| **`infra-spec.yaml`** | The interview's output. A backend renders *from* it; it is not a by-product |

## Commands

```powershell
# Pre-commit checks (read-only). Includes `claude plugin validate` on the plugin
# and the marketplace — it finds the CLI on PATH, or the binary the VS Code
# extension ships, and warns rather than passing quietly if it finds neither.
python3 .claude/skills/git-commit-conventions/scripts/check_repo_consistency.py

# Lays a spec out in canonical form, in place (order, deployment group comments, one-line
# decisions, plugin_version); no value changes, every comment kept. --check writes nothing,
# --no-stamp for a spec only reformatted. The test runs it on a messy spec and the fixtures.
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/write_spec.py <spec>
python plugins/infrastructure-as-skills-azure/core/iac-authoring/tests/run_write_spec_tests.py

# Validates a generated spec. --require-applyable also fails on assumed values and
# open items. Needs PyYAML (pip install pyyaml).
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/check_spec.py <spec>

# The resource-group rules of check_spec.py: a valid split must pass, and each mutation breaks
# one rule (a role that does not exist, a mode missing, a placement into a group that is not there).
python plugins/infrastructure-as-skills-azure/core/iac-authoring/tests/run_spec_tests.py

# Validates every question set (or the paths given) against the format: enum defaults,
# depends_on / from_deployment targets, resolution fields, `resolved_by`, unknown fields.
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/check_question_set.py

# What the interview reads instead of the 2,000-line sets: interview questions, forced_when,
# derived/confirmed/required questions, boundaries. The test asserts it drops none of them.
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/interview_digest.py compute/app-service --language de
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/tests/run_interview_digest_tests.py

# Renders fixture specs with the diagram script and asserts on the .drawio: zones, lines,
# colours, the bundled endpoint icon. The evals cannot draw, so this is where it is tested.
python3 plugins/infrastructure-as-skills-azure/core/iac-diagram/tests/run_diagram_tests.py
# The PNG side: draw.io's broken embedded PNG is repaired, extract/embed round-trips, a diagram
# is verified against its spec, every icon path exists in draw.io's library (needs draw.io for that).
python3 plugins/infrastructure-as-skills-azure/core/iac-diagram/tests/run_png_tests.py

# Checks a rendered pipeline (GitHub, Azure DevOps, GitLab or local) against the
# invariants of references/pipelines.md; the test runner breaks one invariant per
# case in a copy of tests/pipelines/<platform>-<target> and asserts the check names it.
python3 plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_pipeline.py <spec> [--root <dir>]
python3 plugins/infrastructure-as-skills-azure/core/iac-rendering/tests/run_pipeline_tests.py

# The CLAUDE.md section the render leaves in a customer repository: written, replaced when
# older, never overwritten when newer (rev in the begin marker; the block is
# references/claude-md-block.md, its lock claude-md-block.lock). docs/claude-md-sync.drawio.png.
python3 plugins/infrastructure-as-skills-azure/core/iac-rendering/tests/run_claude_md_tests.py
# The version gate: a spec whose spec.plugin_version is newer than the installed plugin halts
# the run (exit 3) so the person is asked to update; older, equal or no version never blocks.
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/tests/run_plugin_version_tests.py

# Writes references/abbreviations.md (the readable abbreviation tables) from naming.default.yaml.
# --check writes nothing; check_repo_consistency.py runs it and fails on a stale file.
python3 plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/write_abbreviations.py

# Renders a spec as the customer's decision document (infra-decisions.md beside it).
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/export_decisions.py <spec> --language de

# A rendered example: fmt, validate, plan-only tests with a mocked platform.
# Every decision in the spec asserted by those tests, or marked not-testable with a reason.
# A per-family render (examples/order-platform/infra): each family module carries its own tests, the root one wiring test.
terraform -chdir=examples/order-platform/infra/modules/app init -backend=false && terraform -chdir=examples/order-platform/infra/modules/app test
terraform -chdir=examples/order-platform/infra init -backend=false && terraform -chdir=examples/order-platform/infra test
python plugins/infrastructure-as-skills-azure/core/iac-rendering/scripts/check_render_coverage.py examples/order-platform/infra/infra-spec.yaml
# The eval dashboard app (eval-agent/dashboard, Node 22): endpoint tests, and the container
# locally with generated data, no Azure and no GitHub (MOCK=1).
npm --prefix eval-agent/dashboard test
pwsh eval-agent/dashboard/run-local.ps1 -Port 8099
```

There is no build. The artefacts are Markdown and YAML; the scripts and the examples'
Terraform tests are the whole verification story. The scripts are Python 3.9+ with PyYAML
as the only dependency: `python3` on macOS, Linux and in a cloud session, `python` or
`py -3` on Windows.

On the owner's Windows machine `claude` is not on `PATH`: the CLI lives at
`~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude.exe`, and the
check script finds it there. In a cloud session it is on `PATH` and nothing needs doing.

## Repository Layout

The full tree is in [README.md](README.md#layout). What is not obvious from it:

| Path | Role |
|---|---|
| `.../core/` | The skills, declared in `plugin.json` as `"skills": ["./core/"]` — it sits beside `skills/`, not inside it |
| `.../core/iac-authoring/` | The entry point. Its description carries the target and workload terms a request says; the interview lives here |
| `.../core/azure-resources/` | Routes every resource to its family and question set. Its description is the keyword surface for resource names |
| `.../core/iac-authoring/questions/deployment.yaml` | The deployment-wide set, resolved before any resource |
| `.../core/iac-authoring/references/{spec,question-set-format,guardrails}.md` | The spec schema; how to author a `questions.yaml`; where every default comes from |
| `.../core/iac-rendering/references/avm.md` | AVM first: which module, status, live version lookup, interfaces, provider requirements, gaps, the test contract |
| `.../core/iac-rendering/references/{naming,terraform-idiom,bicep-idiom}.md` | Naming interfaces; layout, modules, tests per target |
| `.../resources/<family>/routing.md` | Routing table: request → question set. **Not** a `SKILL.md` — see below |
| `.../resources/<family>/<resource>/{questions.yaml,notes.md,terraform.md,bicep.md}` | **The content**, one directory per resource; the rendering references open with the AVM call |
| `.claude/skills/` | Repo maintenance. **Not** shipped with the plugin |

## The Two Structural Constraints

Both are easy to violate by accident and both fail quietly. The measurements behind them
are in [README.md](README.md#why-one-trigger-and-families-that-are-not-skills).

- **`iac-authoring` is the entry, `azure-resources` carries the resource names; families
  are not skills.** Skill descriptions share a character budget (~1% of the context
  window) and are dropped silently when it overflows — the skill stays listed and stops
  matching. So `iac-authoring` triggers on what a request says (target, workload, a few
  resources — "eine Chatapp mit RAG" must match), `azure-resources` on any resource name
  and routes it, the family routes further, the question set is the knowledge unit. New
  resource terms go into `azure-resources`, never into the entry description, which stays
  short. The resource description may be long (cap 1,536 characters); past ~1,200 prune
  the least-typed terms, never split it. `/context` shows the listing after the budget.
- **The groups are declared, not discovered.** `core/` is declared in `plugin.json`;
  `resources/` is deliberately not, so nothing in it costs budget — a family has a
  `routing.md`, never a `SKILL.md`, and the consistency script fails on one. The `skills/`
  scan is one level deep, cannot be switched off, and a declared path that does not
  exist fails to load the plugin: `./patterns/` enters the array in the same commit as
  its first skill.

## Gotchas

- **AVM versions are `0.y.z` and are looked up live, never recalled.** Bicep: the MCR tag
  list; Terraform: the module repo's git tags. The tables in `avm.md` and the resource
  references are dated snapshots. Pin the minor in Terraform (`~> 0.10.0`), the exact
  version in Bicep; re-read the module README's inputs for the version pinned.
- **AVM Terraform modules are moving to AzAPI.** Storage account and virtual network take
  the resource group as `parent_id` (an id) and need `Azure/azapi`, `Azure/modtm` and
  `random` in the root; the Log Analytics module is still `azurerm`-based and pins
  `azurerm` to **4.x** — a root calling it cannot be on 5.x. The root's provider set is
  the union of its modules' requirements.
- **A module default is not the guardrail's default.** Bicep storage defaults to
  `Standard_GRS`, the Bicep workspace to 365 days retention and public access `Enabled`,
  the Terraform storage module to `infrastructure_encryption_enabled = false`. Every
  decision is written on the call, even where it matches.
- **The Terraform storage module's `account_sku_name` overrides tier + replication.**
  Render the SKU name, as Bicep does; the pair is ignored while it is set.
- **The two targets render names differently.** Terraform uses the `LemurDaniel/naming`
  provider with the `Azure::Microsoft.Storage/storageAccounts` identifier. Bicep assembles
  the name from `var`s — the `utility/naming` modules and `genName` are **not ready to
  ship** and generated Bicep must never import them. Every question set declares the
  identifier, the Bicep resource type and the `abbreviation`; use those.
- **The naming provider supersedes the two naming modules.** New generated code uses the
  provider; a repo already on the modules keeps them. Never mix both in one configuration.
- **Authored rendering references target `azurerm` 5.x.** `public_network_access = "Disabled"`
  (string); the 4.x bool is deprecated and `validate` does not warn. The AVM storage
  module takes a **bool** `public_network_access_enabled` — a module input, not the
  provider argument. Check arguments against `terraform providers schema -json` and module
  inputs against the module README rather than memory.
- **A `CLAUDE.md` inside the plugin directory is not loaded as context.** Instructions that
  must reach Claude belong in a skill. This file is at the repo root and does load.
- **Frontmatter `name` must equal the skill's directory name.**
- **Skills carry the rule and its lasting reason, never its history.** No dates, "owner's
  call" or "missed on ..." in a `SKILL.md`: every line is loaded on every use. The
  incident belongs in the commit message or `PROGRESS.md`.
- **Customer-facing wording in a skill is a template for `context.language`.** A German
  block is the German variant, with the English one beside it, never the only text.
- **The plugin never refers to `examples/`.** It ships without them; a live deployment has
  neither the directory nor the specs. Skills, references and question sets carry what they
  need themselves; nothing under `plugins/` - tests and fixtures included - reads from it or
  names one, and `check_repo_consistency.py` fails on `examples/` anywhere under `plugins/`.
  Only the repo's own docs may point at an example.
- **The customer's language is `context.language`** (`en`, `de`), set from the request and
  never asked. The diagram and decision scripts read it; `--language` only overrides it.
- **The spec names decisions, not attributes.** `public_network_access: disabled`, never
  `public_network_access_enabled: false` — that is one backend's spelling leaking into the
  interface the others read.
- **Defaults come from the guardrails, not from the Azure portal.** They diverge routinely
  and in the same direction.
- **A decision that holds for more than one resource belongs in the deployment set.** A
  resource question that re-asks one carries `from_deployment` instead of a `default`.
- **A missing question set is said out loud, never improvised.**
- **The stack is the default.** `context.environments` is `[development, test, production]`
  unless the customer says otherwise; one root, one parameter file and one state (backend
  key, never a workspace) per stage. A `per_environment` value is a parameter from the
  stage file, never a literal in the template; `non_production_default` relaxes cost
  knobs outside production and is refused on anything security-shaped.
- **Only `resolved_by: interview` questions reach the person.** There is no audience
  field: a question is `interview`, `platform` (never asked: derived from the
  landing-zone answers, defaulted or an `open:` entry) or has no `resolved_by` and is defaulted or derived.
- **A change to a rendered tree (`eval-agent/infra/`, `examples/`) goes spec, `check_spec.py`,
  diagram, sign-off, then the render by `iac-rendering` - never a hand edit of the `.bicep`/`.tf`.**
  Small changes follow it too (one app setting, one removed access line). A hand edit is for a
  part the spec names as hand-rendered; after a render, compare it with the code it replaced.
  The block that makes this rule reach a customer repository is step 11 of `iac-rendering`; the
  copies in `eval-agent/CLAUDE.md` and `examples/chat-sandbox/CLAUDE.md` follow it.
- **A render ships with its tests, both targets.** Terraform: one `assert` per spec
  decision, named `# decision: <resource>.<group>.<question>`, what a plan cannot observe
  `# not-testable:` with a reason. Bicep: one entry per decision in `tests/*.armtest.yaml`
  against the compiled ARM (`run_arm_tests.py`; symbolic names via `bicepconfig.json`).
  `check_render_coverage.py` fails on anything else, per target.
- **`check_question_set.py` parses; `check_repo_consistency.py` greps.** Run both before
  a commit that touches a question set: the first finds a default outside `values` or a
  `depends_on` pointing nowhere, the second finds a routing row pointing nowhere.

## Repository Conventions

[.claude/skills/git-commit-conventions/](.claude/skills/git-commit-conventions/SKILL.md)
carries the working rules — read it before committing. In short: commits are authored as
**LemurDaniel \<landau.daniel.1998@gmail.com\>** (set repo-locally only in a tool-driven
session whose identity starts as `Claude`; never touch a configured identity on the
owner's machine); they carry **no attribution trailers** (no `Co-Authored-By`, no "Generated
with Claude Code"); English imperative subject; one concern per commit; never commit to `master` — every
change is a branch and a pull request, and every merge into `master` is a release, so
every branch raises the version in `plugin.json` (the PR check fails otherwise, see
[.claude/skills/release/](.claude/skills/release/SKILL.md)); `PROGRESS.md` is rewritten
before a session's last commit.

`.claude/settings.json` pre-approves the read-only checks and denies force-push,
`reset --hard`, `--no-verify` and `terraform apply`. Do not widen it from a session.

The `origin` remote URL embeds a GitHub personal access token — never copy a remote URL into
a tracked file, a commit message, or command output you paste back.

## The 16-tips review

Run on 2026-10-17 against
https://raw.githubusercontent.com/aishwaryanr/awesome-generative-ai-guide/main/youtube/claude-code-16-tips.md.
Already in place: identity file, examples, the interview, cited sources, progress file,
checks separate from the doing, the deny gate. Changed on that day: the machine-specific
PATH note made conditional, this file's layout and constraint sections cut to the rules
with the derivation left to the README, AVM named in the manifests, the standard checks
added to the allow list. Not applicable: prompt and session habits (T7, T8, T11) and
loops (T13, T16) — the one loop candidate, an AVM version drift check, is a todo in
`PROGRESS.md`.
