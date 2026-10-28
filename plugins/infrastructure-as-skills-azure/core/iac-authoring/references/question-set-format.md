# The question set format

One `questions.yaml` per resource. It and the files beside it are the actual content of
this plugin:

| File | Where | Purpose |
|---|---|---|
| `questions.yaml` | `resources/<family>/<resource>/` | The decisions the resource forces, each with its default, `why` and `renders`. This file's subject |
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
        renders: naming parameter `environment`, tag `environment`

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
        renders: azurerm_storage_account.account_replication_type / sku.name
```

## Where the value comes from

Every question names exactly one answer path: where its value comes from when nobody
states one. `check_question_set.py` fails on a question with none, and on one with two.

| Answer path | The value comes from |
|---|---|
| `default` | The question itself |
| `from_deployment: <id>` | The answer to the deployment-set question with id `<id>` |
| `derived_from` | A customer's answer in the deployment set's `requirements` group, through a map |
| `parameterized: true` | An input of the rendered code (Terraform `variable`, Bicep `param`), filled per stage from that stage's parameter file (`.tfvars`, `.bicepparam`) |
| `required: true` | Nowhere: someone has to state it, or it becomes an `open:` entry |

`from_context: true` reads the spec's `context:` and stands beside `required: true` where
the context value must exist. Whether a question is put to the customer is a different
matter, decided by `resolved_by` alone.

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
| `why` | yes | The reasoning. This is what a reviewer reads and what justifies the default. |
| `renders` | yes | Which attribute(s) the answer drives, per target where they differ. Lets a review skill map code back to a decision. |
| `depends_on` | no | `{ question: <id>, equals: <value> }`, `not_equals`, or `contains` (a `list` question holds the value) — skip unless the condition holds. |
| `from_deployment` | no | The deployment-set question whose answer this one takes. |
| `forced_when` | no | Which answer elsewhere removes a value from `accepts`, or determines this one. Prose, because the conditions are not uniform enough to encode. Recorded as `forced` with `forced_by` in the spec. |
| `from_context` | no | `true`: the value is read from the spec's `context:` under the same id - `environments`, `location`, `subscription_id`, `resource_group_name`. Never asked per resource. With `required: true` beside it, a missing context value becomes an `open:` entry. |
| `resolved_by` | no | Who supplies the value. `interview`: the customer is asked. `derived`: never asked - it follows from interview answers, else its default, else an `open:` entry for the platform team. Absent: never asked - its default or derivation applies, else an `open:` entry for the workload owner. See *Who resolves it*. |
| `topic` | for `interview` | The heading the question stands under in the interview: `platform`, `network`, `security`, `resilience`, `data` or `application`. Only on `resolved_by: interview`. See *The interview's topics*. |
| `plain` | yes | The decision as one sentence in the customer's words, per language (`en` required, `de` and others optional), with `{value}` where the answer goes: "The data is kept {value}." The decision document and the Phase 4 account print every decision through it. See *The customer's line*. |
| `plain_values` | no | What `{value}` becomes for each answer, per language, where the raw value would mean nothing to the customer: `ZRS` → "in three datacenters of the region, so one can fail". Also the label of each option in the interview. Keys are the values in `accepts`, `true`/`false` for a bool, or the options of `offer`. Not needed where the raw value reads fine - a number of days, a name. |
| `offer` | no | Suggestions, not a restriction: on an `interview` question whose answer stays open (an `int`, a free `list`), the options the interview shows, `<option>: { en, de }` with their labels. Any other answer remains valid through "Other" - `mandates` offers GDPR, BSI C5 and ISO 27001 and still takes PCI DSS. Four at most, three for a `list`, whose fourth option is the explicit empty answer. Without it each run invents its own options. Where only the listed answers are valid, it is an `enum` with `accepts` instead. |
| `per_environment` | no | `true` means the value differs per stage: it renders as a parameter whose value lives in each stage's parameter file, never as a literal in the template, and the spec holds a map keyed by stage. See *Stages*. |
| `non_production_default` | no | The value every stage but production takes while `deployment.non_production_savings` is enabled. Cost knobs only: refused in the security, networking, identity, access, DNS, compliance and posture groups. |
| `derived_from` | no | `{ question: <deployment id>, map: { <answer>: <value> } }` — the value follows from a customer's answer in the deployment set's `requirements` group, mapped through this table. See below. |

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
resource question covering the same decision declares `from_deployment: <id>` instead of
a `default` and takes the deployment's answer. A resource that needs a different value
departs from it, recorded `overridden` with a `reason`.

The deployment set's `context` group is the exception: its answers are facts, not
decisions — which stages, which region, which subscription and resource group — and the
spec records them under `context:` as bare values, beside `workload`, `language` and
`tags`, with no `source`. Naming, the pipeline and the decision document read them there.
Everything else in the set is a decision and lands under `deployment:` with its `value`
and `source`. A resource question inherits a fact with `from_context: true` and a
decision with `from_deployment: <id>`.

A deployment set declares `scope: deployment` and names no resource, so it carries no
`resource:` and no `naming:` block, and its groups keep no review order. `from_deployment`
and `derived_from` are refused inside it; `parameterized` belongs only there. Everything
else — groups, ids, `why`, `renders`, `depends_on` — is the same in both scopes.

## Who resolves it: `resolved_by`

The person in front of the interview is the customer - someone who can say what the system
is for and who uses it. A question is put to them only when it says so:

| `resolved_by` | Resolved by | Example | When nobody is there |
|---|---|---|---|
| `interview` | The customer: what the system needs - who uses it, how bad an outage or a loss is, which rules apply, how long data lives | `environment`, `network_exposure`, `blob_soft_delete_days`, `mandates` | Asked - these are the questions the interview exists for |
| `derived` | The environment the workload lands in — landing zone, network, resource groups, pipeline, module source — owned by the platform team | `network_ownership`, `resource_group_mode_main`, `pipeline_auth`, `existing_vnet`, `diagnostics_destination` | Never asked: follows from the interview's answers (`landing_zone_exists`, `central_*`, `deployment_scope`, `deploy_mechanism`, `network_requirements`, …), defaulted where a default exists, otherwise an `open:` entry owned by the platform team |
| *(absent)* | The workload's own technical choice — the guardrail default, or a derivation from a requirement | `min_tls_version`, `private_endpoint_subresources`, `diagnostic_categories`, `key_management` | Defaulted and reported, never asked of a customer; a `required` one becomes an `open:` entry owned by the workload owner |

The field is optional: most questions have none. The test for `interview` is whether the
question can be put in the customer's own words with no Azure vocabulary in it. "How long
must deleted data stay restorable?" passes; "Which subnet should the private endpoint live
in?" does not, however it is phrased - it is `derived`.

A question that inherits its answer (`from_deployment`, `from_context`) is never asked
again: it takes the deployment's answer. It is never `interview`; it repeats `derived` where the question
it inherits from is `derived`, so an open value still goes to the platform team, and
carries none otherwise. A departure on one resource is recorded `overridden` with a
`reason`.

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
        accepts: [LRS, ZRS, GRS, GZRS]
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
  fails on a gap. A value the map cannot reach (`GRS` above) is a departure, recorded
  `overridden`.
- **The default answer derives the guardrail default.** `disruptive` → `ZRS`,
  `one_week` → 7 days, `active` → `Hot`. An unanswered requirement changes nothing; it
  only lets the customer change things. A map whose default-answer row departs from
  [guardrails.md](guardrails.md) is a bug in one of the two.
- **A derived question has no `resolved_by`**: the customer answered the
  requirement; a per-resource departure from the derivation is recorded `overridden`.

What cannot be mapped mechanically stays a question with a default and is named as a
consequence in Phase 4 — `immutability` follows a mandate, but a mandate is free text, so
the consequence is named rather than mapped.

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
```

It parses the files (PyYAML) and checks what a regex cannot: the envelope and both
naming identifiers agreeing; unique group and question ids; the review-order groups in
order; `id`, `ask`, `type`, `why`, `renders` present; a known `type`, `accepts` as a value list
(required on an enum), `{ ref: <kind> }` or `{ catalogue: <file> }` (on a string or a
list, the catalogue existing and parsing), a default within the
accepted values and of the type's kind;
`required`, `default`, `from_deployment`, `derived_from` and `parameterized` mutually
exclusive and one of them present; `depends_on` naming a question in the set and a value it can take;
`from_deployment` and `from_context` naming a deployment-set question; `derived_from` naming an interview question in the deployment
set with a map covering every answer; `resolved_by`, where present, one of `interview`, `derived`;
a `topic` on every interview question and on no other; a question that inherits its answer
never `interview`, and `derived` exactly where its `from_deployment` source is; and
unknown fields, which is how a misspelt `default` turns into a question asked every run.
Exit 0 clean, 1 violations, 2 could not check.

The repo's `check_repo_consistency.py` still runs its regex subset before every commit and
adds what this script does not: routing reachability and the listing budget.
