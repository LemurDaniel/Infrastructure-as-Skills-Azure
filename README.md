# Infrastructure as Skills

> Azure infrastructure authored from the decisions it actually has — rendered as Terraform or Bicep.

A Claude Code plugin. Not a module library and not a template collection: a set of skills
that know **which questions a resource forces you to answer**, and how your answers turn
into code that follows this author's conventions.

## The idea

Writing a storage account is not hard because the HCL is hard. It is hard because a
storage account carries about forty decisions — public network access, TLS floor, shared
key access, replication, soft delete, immutability, which subnet, which private DNS zone,
where diagnostics go — and most of them are invisible until something breaks. Generic code
generation gets the syntax right and the decisions wrong.

So the knowledge in this repo is shaped as a **question set**, not as a template.

## Two layers

**Resources** — one question set per Azure resource type, grouped into families
(`storage`, `network`, `observability`). A single `azure-resources` skill routes any
resource request to the right one. Each question set carries its decisions grouped by
concern:

| Group | Decides |
|---|---|
| Placement | subscription, resource group, region, environment |
| Networking | public access, firewall, private endpoints, DNS |
| Identity | managed identity, RBAC vs. keys, who gets which role |
| Security | encryption, TLS floor, key management, local auth |
| Data protection | retention, soft delete, versioning, immutability |
| Observability | diagnostic settings, which log categories, destination |

Most questions have an opinionated secure default and are never asked — they are *reported*.
Only the decisions that genuinely cannot be defaulted get asked. That distinction is what
keeps the interview short enough to be used.

**Pattern skills** — compose resources into whole systems. A pattern is not a shortcut
around the questions; it is an **answer set** plus the wiring. `private-webapp`
pre-answers thirty of the storage account's questions because the pattern implies them,
asks the four that remain, and then owns what no single question set can: the private
endpoints, the DNS zone links, the role assignments between the parts.

```
private-webapp
├── pre-answers ──> app-service
├── pre-answers ──> storage-account
├── pre-answers ──> key-vault
└── owns the wiring between them
```

## Terraform and Bicep from one question set

The questions are IaC-neutral. Only the rendering differs, so each resource has a
`terraform.md` and a `bicep.md` beside its question set, and Claude reads the one you need.
This is why both targets live in one repo: duplicating the decision knowledge per target
is how the two halves drift apart.

**The decisions land on [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
first.** A resource with a published AVM module — in the
[Terraform](https://azure.github.io/Azure-Verified-Modules/indexes/terraform/) or
[Bicep](https://azure.github.io/Azure-Verified-Modules/indexes/bicep/) index — renders as a
call to it, every decision an explicit input, the version resolved at render time and
pinned in the code. The modules already carry what every hand-written render gets wrong
first: private endpoints with their DNS zone groups, diagnostic settings per sub-resource,
role assignments, locks, customer-managed keys — with the same interface in both targets.
Authored resources are the fallback: for a type without a module, or a repository that
already renders that way. Each resource's rendering reference opens with the decision →
module input mapping and keeps the authored rendering below it.

```
infra-spec.yaml ──> module "storage" { source = "Azure/avm-res-storage-storageaccount/azurerm" ... }
                ──> module storageAccount 'br/public:avm/res/storage/storage-account:0.33.1' = { ... }
```

Rendering targets this author's own naming stack, and hands the rendered name to the module:

- **Terraform** → the [`LemurDaniel/naming`](https://registry.terraform.io/providers/LemurDaniel/naming/latest) provider
- **Bicep** → names assembled from `var`s in the template. The
  [`utility/naming` modules](https://github.com/LemurDaniel/BICEP__Registry/tree/master/modules/utility/naming)
  in `LemurDaniel/BICEP__Registry` are not ready to ship, so generated Bicep does not
  import them

## The spec is the interface

The interview does not produce code. It produces `infra-spec.yaml` — every decision, its
value, and where that value came from (`asked`, `pattern`, `default`, `overridden`). A
backend then renders *from* the spec.

That boundary is the load-bearing part of the design. It makes a review readable at the
level decisions are actually made, turns a regeneration into a diff, and lets the same spec
go to a different backend — including `Infrastructure-by-Skill` for API-driven execution,
which is what makes the two tracks comparable at all.

The spec names decisions, never a backend's attribute spelling:
`public_network_access: disabled`, not `public_network_access_enabled: false`. The mapping
to an attribute lives in the question set's `renders` field and in each target's rendering
reference.

## Layout

```
Infrastructure-as-Skills-Azure/
├── .claude-plugin/marketplace.json
└── plugins/infrastructure-as-skills-azure/
    ├── .claude-plugin/plugin.json
    ├── core/                       # the shared contract
    │   ├── iac-authoring/          # interview protocol, the spec, question-set format
    │   │   ├── questions/deployment.yaml     # posture, network, mandates — asked once
    │   │   ├── references/guardrails.md      # where the defaults come from
    │   │   └── scripts/check_spec.py         # validates an infra-spec.yaml
    │   ├── iac-rendering/          # spec -> Terraform or Bicep: naming, layout, idiom
    │   ├── iac-diagram/            # spec -> infra-diagram.drawio.png for the customer
    │   └── azure-resources/        # the one trigger for every resource -> family
    ├── resources/                  # NOT skills - undeclared, read by azure-resources
    │   ├── storage/
    │   │   ├── routing.md          # routes to the right question set
    │   │   └── storage-account/    # one directory per resource
    │   │       ├── questions.yaml  # the decisions — this is the content
    │   │       ├── notes.md        # what the question set cannot express
    │   │       ├── terraform.md
    │   │       └── bicep.md
    │   ├── network/                # virtual-network
    │   ├── compute/                # app-service
    │   └── observability/          # log-analytics-workspace
    └── patterns/                   # compositions of resource families
```

Planned families: `storage`, `network`, `compute`, `data`, `security`, `observability`.

### Why one trigger, and families that are not skills

Claude Code keeps a listing of every skill's name and description in context, and that
listing has a **shared character budget** — [1% of the model's context
window](https://code.claude.com/docs/en/skills) by default, with each entry capped at 1,536
characters. When it overflows, descriptions get dropped, starting with the least-used
skills. The name survives; the description does not, and the description *is* the
triggering mechanism.

That failure is silent. The skill is installed, it appears in the listing, and nothing
matches it. One report with 160 skills installed kept 20 descriptions and the model found
none of the skills that had lost theirs.

Fifty Azure resources at one skill each would spend the whole budget at once. One skill per
family was the first answer, and it did not survive measurement: five skills cost 1,506 of
~2,000 characters, and the three planned families would have taken it to ~2,450. So there
are three units now — **`azure-resources` triggers, the family routes, the question set
holds the knowledge**. One entry carries the keyword surface for every family at a fifth of
the cost: the 1,536-character cap fits about five family descriptions. Three skills in
total, 954 characters, under half the budget.

The trigger is its own skill rather than part of `iac-authoring` so that a keyword list
growing with every family never crowds out the description of how the protocol works —
both would otherwise share one cap.

### Why the groups are declared, not discovered

`skills/` is scanned exactly one level deep — `<name>/SKILL.md` — and does not recurse, so
nesting inside it would load nothing. The skills therefore live in a scan directory declared
in `plugin.json`:

```json
"skills": ["./core/"]
```

It sits beside `skills/` rather than inside it, because the default `skills/` scan cannot be
switched off and would otherwise treat the group folder as a skill without a `SKILL.md`.
`resources/` is deliberately **not** declared: nothing in it is a skill, so nothing in it
costs budget, and a family's routing table is a `routing.md` that the azure-resources skill
reads by path. A declared path that does not exist fails to load the plugin, which is why
`./patterns/` is not listed yet.

## Examples

[`examples/`](examples/README.md) holds complete runs — request, spec, render, tests — as
the reference for what a good output looks like. `chatbot` is the complex case: twelve kinds
of resource in a spoke network of its own, split into family modules. `chatbot-rag` is a
smaller chat app on Azure AI Foundry with a RAG system, one root, authored resources.

## Install

On Claude Code 2.1.275 or later, one step:

```
/plugin install infrastructure-as-skills-azure --marketplace LemurDaniel/Infrastructure-as-Skills-Azure
```

Before that, the marketplace is added first:

```
/plugin marketplace add LemurDaniel/Infrastructure-as-Skills-Azure
/plugin install infrastructure-as-skills-azure
```

Then just say what you need — `"ich brauch ein storage account für terraform"` — and the
matching skill triggers.

## Status

Early, and the shape matters more than the coverage right now. One interview has been run
end to end; it produced a spec, and the spec is honest about what it could not resolve.
Two specs have been rendered to Terraform, with plan-only tests against mocked providers:
`chatbot` and `chatbot-rag`. Nothing has been applied.

- [x] Plugin skeleton, marketplace manifest, grouped layout
- [x] Shared contract: spec format, question-set format, the interview protocol
- [x] Deployment-wide question set: posture, network ownership, mandates — resolved once,
      inherited by every resource via `from_deployment`
- [x] Rendering: naming interfaces, module layout and idiom per target
- [x] Azure Verified Modules as the primary rendering: the contract, the shared
      interfaces, decision → module input per resource for both targets
- [x] The example re-rendered on AVM, both targets, with its tests — which settled the
      test contract with a module in the middle
- [x] Guardrails: the rules every question set takes its defaults from, shared with
      `Infrastructure-by-Skill`
- [x] Three resources: `storage-account`, `virtual-network`, `log-analytics-workspace`
- [x] A fourth, `app-service` (family `compute`): question set and both rendering references; no rendered example yet
- [x] `check_spec.py` — validates a spec against the contract, and separately whether it
      is applyable at all
- [x] `check_render_coverage.py` — every spec decision asserted by the rendered tests, or
      marked not-testable with a reason; Terraform (`terraform test`) and Bicep
      (`run_arm_tests.py` against the compiled ARM) alike
- [x] `check_question_set.py` — every question set parsed and checked against the format:
      enum defaults, reference targets, resolution fields, `audience`
- [x] The customer interview: every question names its audience, the customer answers six
      requirement questions in their words, the technical decisions are derived from them,
      platform facts come from `platform.yaml`, and the spec renders as a decision document
      (`export_decisions.py`) in the customer's language
- [ ] **Reference pattern skill** — `patterns/` is empty, so composition is specified but
      unproven
- [x] A rendered spec: storage account on a referenced platform, Terraform, validated and
      tested plan-only. Surfaced the `azurerm` 5.x renames and the two-target diagnostics
      (the example has since been removed; the git history holds it)
- [x] The same spec rendered to Bicep, compiled and linted, and diffed against the
      Terraform render — one real divergence found (private endpoint naming) and fixed
      (also removed; the git history holds it)
- [ ] **An applied render.** Neither plan nor what-if has run against a subscription
- [ ] Remaining families: `compute`, `data`, `security`
- [ ] Remaining storage resources: blob container, file share, queue
- [ ] Evals per pattern, plus a consistency run: same spec many times, measure the spread
- [ ] Cross-backend check: one spec through both backends, diff the result

Run `claude plugin validate ./plugins/infrastructure-as-skills-azure` before trusting the manifest
— the grouped `skills` array is the part most likely to be wrong.

## Relation to `Infrastructure-by-Skill`

A sibling repo pointing the other way: it drives a GUI through an agent and records the
run, where this one emits code for a provider to apply.

The split is not simply "no API there, API here". `Infrastructure-by-Skill` is explicitly
an experiment, and part of that experiment is running it against systems that *do* have an
API — otherwise there is no baseline. Without a comparable IaC path next to it, there is no
way to tell whether a guided GUI run is merely slower or actually worse, and no honest
answer to how much of the gap is the approach versus the absence of an API.

So the two repos are not a clean handover. Where both are possible, this one is the
production answer and the other one is the measurement.
