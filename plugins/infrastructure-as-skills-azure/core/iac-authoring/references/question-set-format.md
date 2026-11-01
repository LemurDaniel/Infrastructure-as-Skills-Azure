# The question set format

One `questions.yaml` per resource. It and the files beside it are the actual content of
this plugin:

| File | Where | Purpose |
|---|---|---|
| `questions.yaml` | `resources/<family>/<resource>/` | The decisions the resource forces, each with its default and `why`. This file's subject |
| `render-map.yaml` | beside it | What each decision renders to, per target and implementation - [render-map.md](../../iac-rendering/references/render-map.md) |
| `notes.md` | `resources/<family>/<resource>/` | What a question set cannot express: decisions fixed at creation, dependency order, pitfalls to name out loud |
| `terraform.md` | `resources/<family>/<resource>/` | How the resource's decisions become Terraform: the AVM module with its version snapshot and provider requirements, a decision → module input table, the `azurerm` resource as the fallback, and how to verify arguments against the provider schema |
| `bicep.md` | `resources/<family>/<resource>/` | How the resource's decisions become Bicep: the `br/public:avm/...` module with its version snapshot, a decision → module parameter table, the raw resource type as the fallback, the name length limit, and `bicep build` as the check |
| `models.yaml` | `resources/<family>/<resource>/`, where a question's `accepts: { catalogue: models.yaml }` names it | The Foundry model references: name, version, kind, lifecycle, retirement date, and the regions per deployment type. The interview offers models from this file only, never from memory |
| `routing.md` | `resources/<family>/` | Routes from the family to the resource: a table of the terms a request uses and the question set each one leads to, plus the rules that hold for every resource in the family |

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
        ask:
          en: "Which environment is this for?"
          de: "Für welche Umgebung ist das?"
        type: enum
        accepts: [development, test, qa, uat, integration, staging, preproduction, production, sandbox, demo, hotfix]
        required: true
        why: >
          Drives the rendered name, the tags, and the strictness of several
          defaults below. Nothing sensible can be guessed here.

      - id: replication
        ask:
          en: "Which replication does the data need?"
          de: "Welche Replikation brauchen die Daten?"
        type: enum
        accepts: [LRS, ZRS, GRS, GZRS]
        default: ZRS
        why: >
          ZRS survives a zone loss at roughly LRS cost and is the right floor for
          anything that is not scratch data. GRS only pays off with a documented
          cross-region recovery plan — without one it is cost for a capability
          nobody will exercise.
```

## Where the value comes from

Every question names exactly one answer path: where its value comes from when nobody
states one. `check_question_set.py` fails on a question with none, and on one with two.

| Answer path | The value comes from |
|---|---|
| `default` | The question itself |
| `answer: { deployment: <id> }` | The answer to the deployment-set question with id `<id>`, taken unchanged |
| `answer: { context: <id> }` | The spec's `context.<id>`: `environments`, `location`, `subscription_id`, `resource_group_name`. Missing, it becomes an `open:` entry |
| `answer: { question: <id>, map: {...} }` | A customer's answer to a `requirements` question of the deployment set, translated through the map |
| `parameterized: true` | An input of the rendered code (Terraform `variable`, Bicep `param`), filled per stage from that stage's parameter file (`.tfvars`, `.bicepparam`) |
| `required: true` | Nowhere: someone has to state it, or it becomes an `open:` entry |

`depends_on` and `forced_when` are not answer paths: they apply on top of one, whatever it
is. When another answer holds, `depends_on` drops the question altogether, and
`forced_when` settles its value or removes some of its options - the default, the derivation
or the customer's answer then gives way. Whether a question is put to the customer is a
different matter again, decided by `resolved_by` alone.

## Question fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable key. Referenced by pattern pre-answers and written to `infra-answers.yaml`. Renaming one breaks existing answer files, so treat it as an interface. |
| `ask` | yes | The question as a human would put it, not the attribute name: one line per language (`en` required, `de` and others optional), like `plain`. The interview puts the line in `context.language` and translates only where a language is missing. |
| `type` | yes | One of the types below. |
| `accepts` | for `enum` and a reference | What the answer may be: a list of values (required on an `enum`, optional on a `list`), `{ ref: <kind> }` for a reference to another resource, or `{ catalogue: <file> }` for values from a generated catalogue beside the set. See *Types*. |
| `default` | no | The value taken when nobody states another, from the [guardrails](guardrails.md). It does not decide whether the question is asked - `resolved_by` does; on an `interview` question it is the answer preselected for the customer. |
| `required` | no | `true`: no safe value exists and none can be guessed. An `interview` question is asked; any other becomes an `open:` entry with a placeholder, owned by the platform team (`derived`) or the workload owner. |
| `parameterized` | no | `true` means the value is never asked and never rendered as a literal: the template takes it as an input variable (Terraform `variable`, Bicep `param`) without a default. Used for deployment context that is supplied at deploy time. |
| `answer` | no | Where an inherited answer comes from, in one of three forms: `{ deployment: <id> }` takes a deployment-set answer unchanged; `{ context: <id> }` reads the spec's `context:`; `{ question: <id>, map: { <answer>: <value> } }` translates a customer requirement through a map covering every one of its answers (`outage_impact: disruptive` → `replication: ZRS`). See *Where the value comes from* and *Requirements*. |
| `why` | yes | The reasoning. This is what a reviewer reads and what justifies the default. |
| `renders` | deployment set only | Which attribute(s) the answer drives. A resource set has none: its renderings are its `render-map.yaml`, one record checked against the set, where a second one here drifted from the references. |
| `depends_on` | no | `{ question: <id>, equals: <value> }`, `not_equals`, or `contains` (a `list` question holds the value) — skip unless the condition holds. Gates a question that would be dead otherwise: firewall rules mean nothing while public access is disabled, so they are not asked and discarded. |
| `forced_when` | no | Which answer elsewhere removes a value from `accepts`, or determines this one: `key_protection: hsm` requires Key Vault Premium, and a software key cannot be converted later. The forced value is set, not asked, and recorded as `source: { forced_by: <what drove it> }` in the spec - a value determined silently is worse than one asked, so the spec always names what drove it. Prose, because the conditions are not uniform enough to encode. |
| `resolved_by` | no | Who supplies the value. `interview`: the customer is asked. `derived`: never asked - it follows from interview answers, else its default, else an `open:` entry for the platform team. Absent: never asked - its default or derivation applies, else an `open:` entry for the workload owner. See *Who resolves it*. |
| `topic` | for `interview` | The heading the question stands under in the interview: `platform`, `network`, `security`, `resilience`, `data` or `application`. Only on `resolved_by: interview`. See *The interview's topics*. |
| `plain` | yes | The decision as one sentence in the customer's words, per language (`en` required, `de` and others optional), with `{value}` where the answer goes: "The data is kept {value}." The decision document and the Phase 4 account print every decision through it. See *The customer's line*. |
| `plain_values` | no | What `{value}` becomes for each answer, per language, where the raw value would mean nothing to the customer: `ZRS` → "in three datacenters of the region, so one can fail". Also the label of each option in the interview. Keys are the values in `accepts`, `true`/`false` for a bool, or the options of `offer`. Not needed where the raw value reads fine - a number of days, a name. |
| `offer` | no | Suggestions, not a restriction: on an `interview` question whose answer stays open (an `int`, a free `list`), the options the interview shows, `<option>: { en, de }` with their labels. Any other answer remains valid through "Other" - `mandates` offers GDPR, BSI C5 and ISO 27001 and still takes PCI DSS. Four at most, three for a `list`, whose fourth option is the explicit empty answer. Without it each run invents its own options. Where only the listed answers are valid, it is an `enum` with `accepts` instead. |
| `per_environment` | no | `true` means the value differs per stage: it renders as a parameter whose value lives in each stage's parameter file, never as a literal in the template, and the spec holds a map keyed by stage. See *Stages*. |
| `non_production_default` | no | The value every stage but production takes while `deployment.non_production_savings` is enabled. Cost knobs only: refused in the security, networking, identity, access, DNS, compliance and posture groups. |

### Types

A reference - a subnet, a workspace, a key - is a `string` or a `list` whose `accepts` is
`{ ref: <kind> }`: `resource_group`, `subnet`, `log_analytics_workspace`, `key_vault_key`,
`storage_account`, .... Its value is usually supplied by a pattern or the platform rather
than stated, and never offered as a guessed option.

Values that move faster than a release - the Foundry models - come from a generated
catalogue beside the set: `accepts: { catalogue: models.yaml }`, with `retrieved: <date>` and a
`models` list. The digest prints its newest generally available entries and the interview
offers only those, never one from memory. A workflow regenerates the file, never a hand edit.

| `type` | The value is | Needs | Example |
|---|---|---|---|
| `enum` | One of the values in `accepts` | `accepts: [...]` | `replication`: `accepts: [LRS, ZRS, GRS, GZRS]` |
| `bool` | `true` or `false` | - | `restrict_outbound` |
| `string` | Free text, or with `accepts: { ref: <kind> }` the name or id of another resource of that kind | - | `location`; `private_endpoint_subnet`: `accepts: { ref: subnet }` |
| `int` | A whole number | - | `deployment_capacity` |
| `list` | Several values: from `accepts: [...]` where given, otherwise free; references with `accepts: { ref: <kind> }` | - | `environments`; `subnets`: `accepts: { ref: subnet }` |

## Two scopes

| Order | Scope | Where | Answers |
|---|---|---|---|
| 1 | `deployment` | [`core/iac-authoring/questions/deployment.yaml`](../questions/deployment.yaml) | What holds for everything in one deployment |
| 2 | `resource` (default) | `resources/<family>/<resource>/questions.yaml` | One resource's decisions |

The deployment set's questions are asked first and never restated on a resource. A
resource question covering the same decision declares `answer: { deployment: <id> }`
instead of a `default` and takes the deployment's answer. A resource that needs a different value
departs from it, recorded `source: { overridden: <reason> }`.

Which scope a decision belongs to: could two resources of one system sensibly answer it
differently? Exposure, network ownership, key protection and the diagnostics destination
cannot - one answer per system, so the deployment set. Replication, access tier and
soft-delete windows can, so they stay with the resource; where the customer's requirement
behind them is one per system, the resource question derives its value from it (see
*Requirements*).

The deployment set's `context` group is the exception: its answers are facts, not
decisions — which stages, which region, which subscription and resource group — and the
spec records them under `context:` as bare values, beside `workload`, `language` and
`tags`, with no `source`. Naming, the pipeline and the decision document read them there.
Everything else in the set is a decision and lands under `deployment:` with its `value`
and `source`. A resource question inherits a fact with `answer: { context: <id> }`
and a decision with `answer: { deployment: <id> }`.

A deployment set declares `scope: deployment` and names no resource, so it carries no
`resource:` and no `naming:` block, and its groups keep no review order. `answer` is
refused inside it; `parameterized` belongs only there. Everything
else — groups, ids, `why`, `depends_on` — is the same in both scopes; `renders` is the
deployment set's alone.

## Who resolves it: `resolved_by`

The person in front of the interview is the customer - someone who can say what the system
is for and who uses it. A question is put to them only when it says so:

| `resolved_by` | Resolved by | Example | When nobody is there |
|---|---|---|---|
| `interview` | The customer: what the system needs - who uses it, how bad an outage or a loss is, which rules apply, how long data lives | `environment`, `network_exposure`, `blob_soft_delete_days`, `mandates` | Asked - these are the questions the interview exists for |
| `derived` | The environment the workload lands in — landing zone, network, resource groups, pipeline, module source — owned by the platform team | `network_ownership`, `stage_isolation`, `pipeline_auth`, `existing_vnet`, `diagnostics_destination` | Never asked: follows from the interview's answers (`landing_zone_exists`, `central_*`, `deployment_scope`, `deploy_mechanism`, `network_requirements`, …), defaulted where a default exists, otherwise an `open:` entry owned by the platform team |
| *(absent)* | The workload's own technical choice — the guardrail default, or a derivation from a requirement | `min_tls_version`, `private_endpoint_subresources`, `diagnostic_categories`, `key_management` | Defaulted and reported, never asked of a customer; a `required` one becomes an `open:` entry owned by the workload owner |

The field is optional: most questions have none. The test for `interview` is whether the
question can be put in the customer's own words with no Azure vocabulary in it. "How long
must deleted data stay restorable?" passes; "Which subnet should the private endpoint live
in?" does not, however it is phrased - it is `derived`.

A question that inherits its answer (`answer: { deployment }`, `answer: { context }`) is never asked
again: it takes the deployment's answer. It is never `interview`; it repeats `derived` where the question
it inherits from is `derived`, so an open value still goes to the platform team, and
carries none otherwise. A departure on one resource is recorded
`source: { overridden: <reason> }`.

Keep `interview` for what only the customer knows - a requirement of the system, in their
words - and never for a technical choice with a safe default. There is no cap on their
number: the customer answers multiple choice, and a question not asked is a guess recorded
as their decision.

## The interview's topics: `topic`

The batch is shown in topics, never as one flat list: a customer who is asked about the network
in one place and about the network again six questions later reads it as an interrogation.
Every `interview` question names one; the order below is the order they are asked in.

| `topic` | German | English | What belongs under it |
|---|---|---|---|
| `platform` | Rahmen | Setup | Stages, resource groups and locks, how it is deployed, module and naming source |
| `network` | Netzwerk | Network | Who reaches it and from where, address ranges, DNS ownership, traffic routing |
| `security` | Sicherheit | Security | Mandates, data residency, who may call or administer it, keys, secrets, roles |
| `resilience` | Ausfall | Outage | Outage impact, data-loss tolerance, backup isolation, undeliverable messages |
| `data` | Daten | Data | Access pattern, retention, containers, shares, queues |
| `application` | Anwendung | Application | What the workload does with the resource: OS, licence, publisher, channels, ordering |

The `topic` is the heading the customer sees the question under in the interview, chosen
by what the conversation is about. It is independent of the question's group
(`groups[].id`), which only orders the YAML file. `data_residency` is filed in the
`requirements` group beside `outage_impact`, but a customer talks about where
data may live together with mandates and data protection, so its topic is `security`.

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
  A question inheriting a per-stage deployment question through `answer: { deployment }` is
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
(`answer: { question, map }`) is production's, and the non-production stages take the savings default
where one exists.

## Requirements, and derived answers

Some resource decisions follow from something only the customer can say - how bad an
outage would be, how far back a delete must be recoverable, how the data is used. The
customer is not asked them per resource, nor in the resource's vocabulary ("LRS or ZRS?").
The deployment set's `requirements` group asks once, in the customer's words
(`outage_impact`, `data_loss_tolerance`, `data_access_pattern`, `backup_isolation`,
`data_residency`), and each resource question **derives** its value from that answer:

```yaml
# deployment.yaml - asked of the customer
      - id: outage_impact
        type: enum
        accepts: [tolerable, disruptive, critical]
        default: disruptive
        resolved_by: interview

# storage-account/questions.yaml - derived, never asked
      - id: replication
        type: enum
        accepts: [LRS, ZRS, GRS, GZRS]
        answer:
          question: outage_impact
          map: { tolerable: LRS, disruptive: ZRS, critical: GZRS }
```

`question` names the requirement; `map` is the translation table, one row per answer the
customer can give and the value this question takes for it. The customer says
`disruptive`, the storage account gets `ZRS`.

The map sits on the resource question, not on the requirement: the resource knows its own
values (`ZRS`), the requirement only the customer's (`disruptive`), and a new resource
derives from an existing requirement without touching the deployment set. The spec records
the result as `source: { derived_from: deployment.outage_impact }`; the
decision document turns that into "because you said an outage would be disruptive, the
data is kept in three datacenters".

Three rules:

- **Every answer maps.** The map has a row for every answer the requirement can take; the
  check fails on a missing one. A value no row reaches (`GRS` above) can still be chosen, as
  a departure recorded `overridden`.
- **Silence changes nothing.** The requirement's default answer maps to the guardrail
  default (`disruptive` → `ZRS`, `one_week` → 7 days, `active` → `Hot`), so a customer who
  says nothing gets the baseline. If the map and [guardrails.md](guardrails.md) disagree
  there, one of them is wrong.
- **The derived question is not asked.** The customer answered the requirement, so the
  resource question carries no `resolved_by`.

Where no table can do the mapping - a mandate is free text, so "GoBD → immutable blobs"
cannot be a map - the question keeps a default and Phase 4 names the consequence instead.

## Rules that matter

**Default to the secure value, not the portal default.** Azure ships public network access
and shared keys enabled; the defaults come from [guardrails.md](guardrails.md), which
inverts them, never from the portal.

**`why` is not decoration.** It is the only artefact that survives into review. "Secure
default" is not a `why`; the `why` is what breaks if the other value is chosen, or what it
costs. If you cannot write one, the question probably does not belong in the set.

**Keep `required` for what nobody can guess.** A `required` question that is not asked
becomes an `open:` entry that blocks the apply until someone answers it. Use it for what only
the environment knows - the subnet, the workspace, the key it connects to - never for a
choice with a safe default.

**Group order is review order.** placement → networking → identity → security →
data_protection → observability. Keep it, because a reviewer reading three different
resources should not have to relearn the layout each time.

## Validate

```powershell
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py                       # every set in the plugin
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py resources/storage      # one family, one resource, or one file
```

It parses every set and checks the rules of this document; the full list is in the
script's docstring. Unknown fields are reported too - a misspelt `default` is a question
with no answer path. Exit 0 clean, 1 violations, 2 could not check.
