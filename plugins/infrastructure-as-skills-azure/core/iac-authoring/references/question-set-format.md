# The question set format

One file per resource, at `resources/<family>/<resource>/questions.yaml` — beside the
resource's `notes.md`, `terraform.md` and `bicep.md`. These files are the actual content of
this plugin; a family's `routing.md` is a router and a handful of family-wide truths.

## Two scopes

| Scope | Where | Answers |
|---|---|---|
| `resource` (default) | `resources/<family>/<resource>/questions.yaml` | One resource's decisions |
| `deployment` | [`core/iac-authoring/questions/deployment.yaml`](../questions/deployment.yaml) | What holds for everything in one deployment |

The deployment set is resolved **first**, and a resource question that would re-ask one of
its decisions declares `from_deployment: <id>` instead of a default. Posture is one
decision per system, not one per resource — asking "should this be reachable from the
internet?" eight times in one run is the failure this prevents, and so is answering it
differently the eighth time.

A deployment set names no resource, so it carries no `resource:` and no `naming:` block,
and the consistency script exempts it from those checks. Everything else — groups, ids,
`why`, `renders`, `depends_on` — is identical.

## Shape

```yaml
schema_version: 1

resource: Microsoft.Storage/storageAccounts
title: Azure Storage Account

# Both identifier forms, because the two targets spell them differently, plus the
# abbreviation the Bicep side renders into a var (the naming modules are not shipped).
naming:
  terraform: "Azure::Microsoft.Storage/storageAccounts"
  bicep: "Microsoft.Storage/storageAccounts"
  abbreviation: "st"

# What this resource cannot do, so the skill can hand off instead of improvising.
boundaries:
  - "Does not create the resource group; expects one (see placement.resource_group)."
  - "Private DNS zones are shared infrastructure — a pattern skill owns them."

groups:
  - id: placement
    title: Placement
    questions:
      - id: environment
        ask: Which environment is this for?
        type: enum
        values: [development, test, qa, uat, integration, staging, preproduction, production, sandbox, demo, hotfix]
        required: true
        why: >
          Drives the rendered name, the tags, and the strictness of several
          defaults below. Nothing sensible can be guessed here.
        renders: naming parameter `environment`, tag `environment`

      - id: replication
        ask: Which replication does the data need?
        type: enum
        values: [LRS, ZRS, GRS, GZRS]
        default: ZRS
        confirm_in: [production]
        why: >
          ZRS survives a zone loss at roughly LRS cost and is the right floor for
          anything that is not scratch data. GRS only pays off with a documented
          cross-region recovery plan — without one it is cost for a capability
          nobody will exercise.
        renders: azurerm_storage_account.account_replication_type / sku.name
```

## Question fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable key. Referenced by pattern pre-answers and written to `infra-answers.yaml`. Renaming one breaks existing answer files, so treat it as an interface. |
| `ask` | yes | The question as a human would put it. Not the attribute name. |
| `type` | yes | `enum`, `bool`, `string`, `int`, `list`, `ref` |
| `values` | for `enum` | Allowed values. |
| `default` | no | The opinionated value. Its presence is what makes the question not get asked. |
| `required` | no | `true` means no default exists and it must be asked. Mutually exclusive with `default`. |
| `parameterized` | no | `true` means the value is never asked and never rendered as a literal: the template takes it as an input variable (Terraform `variable`, Bicep `param`) without a default. Used for deployment context that is supplied at deploy time. Mutually exclusive with `default` and `required`. |
| `confirm_in` | no | Environments where the default is surfaced for confirmation rather than applied silently. |
| `why` | yes | The reasoning. This is what a reviewer reads and what justifies the default. |
| `renders` | yes | Which attribute(s) the answer drives, per target where they differ. Lets a review skill map code back to a decision. |
| `depends_on` | no | `{ question: <id>, equals: <value> }`, or `not_equals` — skip unless the condition holds. |
| `ref` | for `ref` | What the value points at, e.g. `subnet`, `log_analytics_workspace`. Signals that a pattern usually supplies it. |
| `from_deployment` | no | The deployment-set question whose answer this one takes. Mutually exclusive with `default` and `required`. |
| `forced_when` | no | Which answer elsewhere removes a value from `values`, or determines this one. Prose, because the conditions are not uniform enough to encode. Recorded as `forced` with `forced_by` in the spec. |
| `from_context` | no | The value comes from the spec's `context:` rather than being asked per resource. |
| `audience` | yes | Who answers it: `customer`, `engineer` or `platform`. See below. |
| `plain` | yes | One line per language (`en` required, `de` and others optional) saying what the decision means to the customer, with `{value}` where the value goes. Read by the decision document. See below. |
| `plain_values` | no | For an enum, list or bool: the customer's words for each value, per language — what `{value}` becomes. Keys are the question's values. |
| `per_environment` | no | `true` means the value differs per stage: it renders as a parameter whose value lives in each stage's parameter file, never as a literal in the template, and the spec holds a map keyed by stage. See *Stages*. |
| `non_production_default` | no | The value every stage but production takes while `deployment.non_production_savings` is enabled. Cost knobs only: refused in the security, networking, identity, access, DNS, compliance and posture groups. |
| `derived_from` | no | `{ question: <deployment id>, map: { <answer>: <value> } }` — the value follows from a customer's answer in the deployment set's `requirements` group, mapped through this table. Mutually exclusive with `default`, `required` and `from_deployment`. See below. |

## Who answers: `audience`

The person in front of the interview is, by default, the customer — someone who can say
what the system is for and who uses it, and who cannot say which subnet carries private
endpoints. Every question therefore names who can answer it, and the interview puts a
question only to the audience that can:

| `audience` | Can answer | Example | When nobody of that audience is there |
|---|---|---|---|
| `customer` | What the system needs: who uses it, how bad an outage or a loss is, which rules apply, how long data lives | `environment`, `network_exposure`, `replication`, `blob_soft_delete_days`, `mandates` | Asked — these are the questions the interview exists for |
| `engineer` | A technical choice of the workload's engineer, with a safe default from the guardrails | `min_tls_version`, `private_endpoint_subresources`, `diagnostic_categories`, `key_management` | Defaulted and reported, never asked of a customer; a `required` one becomes an `open:` entry owned by the engineer |
| `platform` | A fact of the organisation's platform, the same for every deployment on it | `landing_zone`, `existing_vnet`, `private_endpoint_subnet`, `private_dns_records`, `diagnostics_destination` | Read from [`platform.yaml`](platform.md); without one, defaulted where a default exists and otherwise an `open:` entry owned by the platform team |

The test for `customer` is whether the question can be put in the customer's own words
with no Azure vocabulary in it. "How long must deleted data stay restorable?" passes;
"Which subnet should the private endpoint live in?" does not, however it is phrased —
it is `platform`. An inherited question (`from_deployment`, `from_context`) carries the
audience that may override it per resource, which is usually `engineer`.

Keep `customer` for what only the customer knows - a requirement of the system, in their
words - and never for a technical choice with a safe default. There is no cap on their
number (the cap of six was dropped on 2026-10-24: the customer answers multiple choice,
and a question not asked is a guess recorded as their decision); the test is the one
above, whether the question can be put without Azure vocabulary.

## The customer's line: `plain` and `plain_values`

`why` is for the reviewer; `plain` is for the customer. One line per language, in the
customer's words, with `{value}` where the decision's value goes — and, where a raw value
would mean nothing to them, `plain_values` giving the words per value:

```yaml
        plain:
          en: "The data is kept {value}."
          de: "Die Daten liegen {value}."
        plain_values:
          LRS:  { en: "three times in one datacenter", de: "dreifach in einem Rechenzentrum" }
          ZRS:  { en: "in three datacenters of the region, so one can fail", de: "in drei Rechenzentren der Region, eines darf ausfallen" }
```

The decision document (`scripts/export_decisions.py`) renders every decision in the spec
through these: a `requirement` value becomes "because you said *disruptive* → the data is
kept in three datacenters", a default becomes a line under "set by the rules". `en` is
required, because the document falls back to it and says so; the plugin's own sets carry
`de` as well. A line without `{value}` is fine where the value is implied (a `required`
reference); a bool or enum without `plain_values` prints the raw value, which is rarely
what a customer should read.

## Stages: `per_environment` and `non_production_default`

One code base is deployed through a stack of stages — `context.environments`, default
`[development, test, production]`, a `[sandbox]` for the throwaway case — each from its
own parameter file with its own state. Two fields say how a decision behaves across them:

- **`per_environment: true`** marks a value that differs per stage by nature: an address
  range, a subnet prefix, the subscription and resource group, a referenced hub, subnet or
  workspace. It is never a literal in the template. The render makes it a parameter and
  writes each stage's value into that stage's file; the spec holds the values as a map
  keyed by stage, and a stage nobody could answer for is an `open:` entry naming the stage.
  A question inheriting a per-stage deployment question through `from_deployment` is
  per-stage too, and the check says so.
- **`non_production_default`** is the value every stage but production takes while
  `deployment.non_production_savings` is enabled (the default): `replication: LRS`,
  `log_retention_days: 30`. A stack with no production stage (`[sandbox]`) takes it in
  every stage by rule, without the question (`forced`, by `environments`). It exists for cost and for nothing else — the check refuses
  it in the security, networking, identity, access, DNS, compliance and posture groups,
  because a development stage that is less secure than production is where the breach
  happens. Everything else is identical in every stage: parity is what the stack is for.

A value the customer states holds in every stage unless they say which stage they mean —
the savings relax defaults and derived values, never a stated one. A derived value
(`derived_from`) is production's, and the non-production stages take the savings default
where one exists.

## Requirements, and `derived_from`

A resource question whose answer the customer could give — how much redundancy, how far
back a delete must be recoverable, how the data is used — is not asked per resource and
not asked in the resource's vocabulary. The deployment set's `requirements` group asks it
once, in the customer's terms (`outage_impact`, `data_loss_tolerance`,
`data_access_pattern`, `backup_isolation`, `data_residency`), and the resource question
**derives** its value:

```yaml
      - id: replication
        type: enum
        audience: engineer
        values: [LRS, ZRS, GRS, GZRS]
        derived_from:
          question: outage_impact
          map: { tolerable: LRS, disruptive: ZRS, critical: GZRS }
```

The map lives on the resource question, not on the requirement: the resource knows its
own vocabulary, and a new resource derives from an existing requirement without editing
the deployment set. The spec records the value with `source: requirement` and
`derived_from: deployment.outage_impact`, which is what lets the decision document say
"because you said an outage would be disruptive, the data is kept in three datacenters".

Three rules:

- **Every answer maps.** The map covers every value the requirement can take; the check
  fails on a gap. A value the map cannot reach (`GRS` above) is an engineer's departure,
  recorded `overridden`.
- **The default answer derives the guardrail default.** `disruptive` → `ZRS`,
  `one_week` → 7 days, `active` → `Hot`. An unanswered requirement changes nothing; it
  only lets the customer change things. A map whose default-answer row departs from
  [guardrails.md](guardrails.md) is a bug in one of the two.
- **A derived question's `audience` is `engineer`**: the customer answered the
  requirement; a per-resource departure from the derivation is the engineer's.

What cannot be mapped mechanically stays an engineer's question with a default and is
named as a consequence in Phase 4 — `immutability` follows a mandate, but a mandate is
free text, so the engineer names it rather than a table.

## Rules that matter

**Default to the secure value, not the portal default.** They diverge, routinely and in
the same direction. `public_network_access` and `shared_access_key_enabled` are the classic
pair: Azure ships them permissive, and inheriting that as a baseline means every resource
this plugin generates starts from the wrong end.

**A decision that holds for more than one resource belongs in the deployment set.** The
test is whether two resources could sensibly answer it differently. Posture, network
ownership, key protection and the diagnostics destination fail that test — they are one
answer per system. Replication, access tier and soft-delete windows pass it, and stay with
the resource.

**One answer may force another.** `key_protection: hsm` is not a flag; it requires Key
Vault Premium, and a software key cannot be converted in place later. Where that happens,
the forced value is pre-answered rather than asked, and the question that forced it is
named in the spec. A question whose answer is already determined is noise, but a *silently*
determined one is worse — say which mandate drove it.

**`why` is not decoration.** It is the only artefact that survives into review. "Secure
default" is not a `why`; the `why` is what breaks if the other value is chosen, or what it
costs. If you cannot write one, the question probably does not belong in the set.

**Keep `required` scarce.** Every required question is paid on every run forever. In
practice a resource has two or three genuinely un-guessable decisions — environment,
region, and what it connects to. The rest can default.

**Group order is review order.** placement → networking → identity → security →
data_protection → observability. Keep it, because a reviewer reading three different
resources should not have to relearn the layout each time.

**`depends_on` instead of asking dead questions.** Firewall rules are meaningless when
public access is disabled. Gate them rather than asking and discarding.

## Validate

```powershell
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py                       # every set in the plugin
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py resources/storage      # one family, one resource, or one file
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py --platform ./platform.yaml   # a platform profile against the deployment set
```

It parses the files (PyYAML) and checks what a regex cannot: the envelope and both
naming identifiers agreeing; unique group and question ids; the review-order groups in
order; `id`, `ask`, `type`, `why`, `renders` present; a known `type`, `values` on an
enum, a default within `values` and of the type's kind, `ref` on a ref question;
`required`, `default`, `from_deployment` and `parameterized` mutually exclusive and one
of them present; `depends_on` naming a question in the set and a value it can take;
`from_deployment` and `from_context` naming a deployment-set question; `confirm_in`
naming known environments; `derived_from` naming a customer question in the deployment
set with a map covering every answer; `audience` present and one of `customer`, `engineer`,
`platform`; and
unknown fields, which is how a misspelt `default` turns into a question asked every run.
Exit 0 clean, 1 violations, 2 could not check.

The repo's `check_repo_consistency.py` still runs its regex subset before every commit and
adds what this script does not: routing reachability and the listing budget.
