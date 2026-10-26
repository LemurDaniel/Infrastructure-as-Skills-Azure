# `infra-spec.yaml` — the handover interface

The interview does not produce code. It produces a **spec**, and the spec is what a backend
renders. Keeping that boundary sharp is the most load-bearing decision in this design.

## Why a spec and not direct generation

Three things fall out of it that direct generation cannot give you:

**It is the contract between backends.** The same spec can be rendered as Terraform or as
Bicep. Without a spec in the middle, each backend grows its own private notion of what was
decided, and there is nothing to compare. With one, sending a single spec through both
backends and diffing the result is a test you can actually run.

**It is reviewable at the level decisions are made.** HCL records the *result* of a
decision and never the decision itself. `public_network_access_enabled = false` tells you
the value and nothing about whether anyone chose it. That gap is where infrastructure
review turns into archaeology.

**It makes regeneration a diff.** Re-running against an existing spec normally asks
nothing and changes nothing, so the diff shows precisely what moved — rather than a
rewrite nobody can audit.

## Shape

```yaml
schema_version: 1

spec:
  id: payments-api-prod
  target: terraform          # terraform | bicep
  generated_by: infrastructure-as-skills-azure
  plugin_version: 0.0.2      # the plugin that last wrote this file; an older plugin halts on it
  skill: private-webapp
  skill_version: 0.1.0
  at: 2026-10-17T09:14:00Z

# Values every resource inherits. Resolved once, not per resource. The system is
# deployed through a stack of stages from one code base; what differs per stage is a
# map keyed by stage, rendered as a parameter whose value lives in the stage's file.
context:
  environments: [development, test, production]
  language: de               # the customer's language (en | de): the picture, the decision document, the customer-facing text
  # location, subscription_id and resource_group_name are never asked: what the request
  # states is written here, what it does not is an open: entry and a placeholder in the
  # stage file. A resource group the render creates needs no name here.
  location: westeurope
  workload: payments
  subscription_id:
    development: 00000000-0000-0000-0000-00000000dev1
    test: 00000000-0000-0000-0000-00000000tst1
    production: 00000000-0000-0000-0000-00000000prd1
  resource_group_name:
    development: rg-we-dev-payments-01
    test: rg-we-tst-payments-01
    production: rg-we-prod-payments-01

  # The tag set this repository uses, taken from it rather than prescribed here.
  tags:
    cost_center: CC-4711
    owner_team: payments

# The deployment set's answers. Resolved once; every resource inherits them.
deployment:
  # How the code reaches Azure - see "Delivery: the pipeline" below.
  deploy_mechanism:
    value: github               # azure_devops | github | gitlab | local
    source: stated
  pipeline_auth:
    value: workload_identity    # not written when deploy_mechanism is local
    source: default
  pipeline_approvals:
    value: production           # production | every_stage | none
    source: default
  deployer_roles:               # derived, never asked: what the deploying identity needs beyond Contributor
    value:
      - { role: Key Vault Secrets Officer, scope: key-vault, for: [resources.key-vault.security.secret_placeholders] }
    source: forced
    forced_by: [resources.key-vault.security.secret_placeholders]
  network_exposure:
    value: private
    source: asked
  local_auth:
    value: disabled
    source: default
  network_ownership:
    value: create
    source: asked
  # Resource groups: `context.resource_group_name` is the `main` group. A listed role
  # is a group of its own; each group is `existing` (name from the stage file) or
  # `create` (the render makes it). Per resource: `placement.resource_group: <role>`
  # departs from the role table in iac-rendering/references/resource-groups.md.
  resource_group_layout:
    value: split                # single | split
    source: asked
  resource_group_scheme:
    value: concern              # concern | lifecycle | protection | component
    source: asked
  resource_group_split:         # derived from the scheme and the resources in the design
    value: [network, data]
    source: forced
    forced_by: deployment.resource_group_scheme
  resource_group_mode_main:
    value: create
    source: asked
  resource_group_mode_network:
    value: existing
    source: default
  resource_group_mode_data:
    value: create
    source: asked
  address_space:
    # per_environment: one value per stage, never a literal in the template. A stage
    # nobody could answer for is missing here and named in open: below.
    value:
      development: 10.42.0.0/16
      test: 10.43.0.0/16
      production: 10.44.0.0/16
    source: asked
  private_endpoint_subnet:
    value: snet-data-prod-01
    source: asked
  private_dns_ownership:
    value: platform
    source: default
  mandates:
    value: [BSI C5]
    source: stated
  key_protection:
    value: hsm
    source: stated
    forces:                      # what this answer determined elsewhere
      - key-vault.sku: premium

# Present only when a pattern drove the run.
pattern:
  id: private-webapp
  resources: [app-service, storage-account, key-vault]

# How the rendered code is split. Both targets have a module concept, so the split
# is decided once here rather than twice in two renderers.
composition:
  granularity: per-concern     # single | per-concern | per-resource
  source: default

  modules:
    - id: storage
      contains: [storage-account]
      inputs: [environment, location, workload, resource_group_name]
      outputs: [id, name, principal_id]

    - id: storage-network
      contains: [private-endpoint, private-dns-record]
      needs: [storage]         # consumes storage.id
      inputs: [subnet_id, dns_zone_id]
      outputs: [private_endpoint_ip]

resources:
  storage-account:
    networking:
      public_network_access:
        value: disabled
        source: pattern
      private_endpoint_subnet:
        value: snet-data-prod-01
        source: asked
    security:
      shared_access_key_enabled:
        value: false
        source: pattern
      min_tls_version:
        value: TLS1_2
        source: default
    data_protection:
      blob_soft_delete_days:
        value: 7
        source: default

# Decisions that belong to no single resource. The pattern owns these.
wiring:
  # Which zone belongs to which endpoint: iac-rendering/references/private-dns-zones.md
  private_dns_zones:
    value: [privatelink.blob.core.windows.net, privatelink.vaultcore.azure.net]
    source: pattern
  role_assignments:
    value:
      - from: app-service
        to: storage-account
        role: Storage Blob Data Contributor
    source: pattern
  # Read by the diagram (core/iac-diagram), optional: who reaches what, what a
  # resource is for, and what is optional. `from`/`to` are resource keys or actors
  # (internet, users, external:<name>).
  access:
    value:
      - { from: users, to: app-service, label: HTTPS 443 }
      - { from: app-service, to: storage-account }
    source: stated
  purposes:
    value: { app-service: Webshop frontend, storage-account: Product images }
    source: stated
  optional:
    value: [redis-cache]
    source: stated
```

## Language

`context.language` is the customer's language, `en` or `de`: the fixed labels of the picture,
the decision document and every customer-facing text in the spec (`wiring.purposes`,
`wiring.access[].label`, the `owner` and `question` of an `open:` entry) are written in it.
Phase 0 sets it from the language the request and the answers are written in; it is never
asked. The scripts read it (`new_diagram.py`, `verify_diagram.py`, `export_decisions.py`) and
their `--language` only overrides it for a check. A spec without it is drawn in English and
`check_spec.py` warns. Keys, values, `why` and `reason` stay English whatever it says.

## Stages: one value or a map

`context.environments` lists the stages the code is deployed through — `[development,
test, production]` by default, `[sandbox]` for one throwaway environment. Every value in
the spec is then either **one value for every stage** (a scalar, a list, a reference
object) or **a map keyed by stage**:

```yaml
      replication:
        value: { development: LRS, test: LRS, production: ZRS }
        source: requirement
        derived_from: deployment.outage_impact
        non_production: default     # dev and test took the question's non_production_default
```

A map is required for a `per_environment` question (the value differs per stage by
nature: ranges, subscriptions, referenced platform parts) and allowed for any other where
a stage departs — a cost saving (`non_production_default`), or a departure the user named
for that stage, recorded `overridden`. A posture decision is never a map otherwise: one
posture per system, and `check_spec.py` refuses a stage split on a question that is neither
`per_environment` nor a cost knob unless its source is `overridden`. Its keys are a
subset of `context.environments`; a stage missing from the map is an `open:` entry that
names the stage:

```yaml
open:
  - key: deployment.address_space
    environments: [test, production]
    question: Which address ranges are assigned to the test and production stages?
    owner: network / IPAM owner
    blocks: apply
```

`non_production: default` marks the stages that took the question's
`non_production_default` under `deployment.non_production_savings`; a stage the user set
differently carries `non_production: stated`. The renderer reads a map as a parameter
and writes each stage's value into that stage's parameter file; a scalar is a literal in
the template. A reference object (`{ name, resource_group_name }`) is told apart from a
stage map by its keys, which are never stage names.

**An open stage is still rendered, with placeholders.** A stage named in an `open:` entry
gets its parameter file (`environments/<stage>.tfvars`, `main.<stage>.bicepparam`) and its
pipeline block anyway, so the scaffold stands and answering the entry is an edit of values.
An open per-stage value renders as the all-zero GUID `00000000-0000-0000-0000-000000000000`
(an id) or `OPEN-<what>` (a name); what the spec does know stays real. The spec carries no
placeholder - it carries the `open:` entry - and `check_pipeline.py` fails both ways: an open
stage whose file holds no placeholder (the values were guessed) and a resolved stage whose
file still holds one. A placeholder never deploys; the pipeline refuses it
([pipelines.md](../../iac-rendering/references/pipelines.md), invariant 11), and the stage
chain then holds every stage behind it.

## Resource groups: roles, modes, names

`context.resource_group_name` is the **main** group of a single layout: one group per stage that
holds everything. A split has no main group - every resource is in the group of its scheme's
role, and the Bicep root deploys into the first of them. Splitting is a deployment decision; the
keys it leaves in the spec:

| Key | Holds | Notes |
|---|---|---|
| `deployment.resource_group_layout` | `single` or `split` - asked | `single` or absent: one group, nothing below is written |
| `deployment.resource_group_scheme` | `concern` (`network`, `data`, `application`, `observability`, `security`), `lifecycle` (`foundation`, `state`, `runtime`), `protection` (`protected`, `standard`), `component` (`shared` and the parts) - asked on `split` | Absent means `concern`, which is what a spec written before the key holds |
| `deployment.resource_group_components` | Under `component` only: the system's parts, short lowercase names (`chat`, `ingest`) | Derived by the run from the description and `wiring.purposes`, `forced_by: wiring.purposes`; every resource that is not shared names its part in `placement.resource_group` |
| `deployment.resource_group_split` | The roles with a group of their own, derived: every role of the scheme that a resource of the design belongs to | `forced` by the scheme; a group the person drops or adds at the sign-off is `overridden`. `check_spec.py` refuses a role of another scheme |
| `deployment.resource_group_mode_<role>` | `existing` or `create`, for `main` and for every listed role | An unlisted role has no mode - it is part of `main` |
| `deployment.resource_group_lock` | `production`, `all_stages`, `none` | Only groups in mode `create` get a lock |
| `deployment.resource_lock` | `production`, `all_stages`, `none` | A `CanNotDelete` lock on each resource that holds data or state, in the stages named; see [avm.md](../../iac-rendering/references/avm.md#the-shared-interfaces) for which kinds |
| `context.resource_group_name_<role>` | The name of the group, a stage map like `resource_group_name` | `main` keeps `context.resource_group_name`. Optional, like it: recorded when the customer or the platform stated it, otherwise a parameter the stage file supplies. For a `create` group a stated name is used verbatim; without one the render computes it from the naming interface. Never for a role that is not split off |
| `resources.<key>.placement.resource_group` | One role, for a resource that departs from its kind's role | `source: overridden` with a `reason`; without the key the kind's role applies |

```yaml
context:
  resource_group_name:                  # main, mode create: the name is a parameter of the stage
    production: rg-chatbot-prod-we
  resource_group_name_network:          # network, mode existing: the platform handed it out
    production: rg-spoke-chatbot-prod-we
deployment:
  resource_group_layout: { value: split, source: asked }
  resource_group_scheme: { value: concern, source: asked }
  resource_group_split: { value: [network, data], source: overridden, reason: application and security stay in main }
  resource_group_mode_main: { value: create, source: asked }
  resource_group_mode_network: { value: existing, source: asked }
  resource_group_mode_data: { value: create, source: asked }
resources:
  storage-account__host:
    placement:
      resource_group:
        value: data
        source: overridden
        reason: The Function App's own state is kept with the data, not with the app.
```

- **Which kind belongs to which role** is one table,
  [resource-group-roles.yaml](../../iac-rendering/references/resource-group-roles.yaml); the
  diagram and the decision document read it, the prose is
  [resource-groups.md](../../iac-rendering/references/resource-groups.md). A private endpoint is
  in the group of the resource it serves and has no row.
- **A group's name is a parameter, never asked and never invented** - as for the main group
  (`deployment.yaml`, `resource_group_name`): a `create` group's name is computed by the render;
  an `existing` group's name is stated or, per stage, an `open:` entry with `OPEN-resource-group`
  in the stage file. A stage the spec's stage map leaves out is the generic per-stage rule above.
- **Stage isolation by resource group forces `existing`.** Under `deployment.stage_isolation:
  resource_group` every `resource_group_mode_<role>` is `existing` (`forced`, `forced_by:
  deployment.stage_isolation`) and no deployer role is scoped to `subscription`: a role on the
  shared subscription reaches every stage. Each stage's identity holds its roles on its own
  groups; `check_spec.py` fails on either breach.
- **A mode change is not an edit of a value.** `existing` <-> `create` creates, deletes or orphans
  a real group; the next run says so before it writes, and the pipeline refuses a Terraform plan
  that deletes one ([pipelines.md](../../iac-rendering/references/pipelines.md), invariant 12).

## Delivery: the pipeline

Four deployment keys say how the rendered code is deployed. They are a render output beside
the Terraform or Bicep, drawn from the same spec; the files per system, the flow and the
invariants are in [pipelines.md](../../iac-rendering/references/pipelines.md).

| Key | Values | Default | Source |
|---|---|---|---|
| `deploy_mechanism` | `azure_devops`, `github`, `gitlab`, `local` | none - asked | `stated`, `asked`, or `carried` when the repository already holds `.github/workflows`, `azure-pipelines.yml` or `.gitlab-ci.yml` |
| `pipeline_auth` | `workload_identity`, `client_secret` | `workload_identity` | `default`; `client_secret` only `stated` by the platform team, with the rotation as an `open:` entry |
| `pipeline_approvals` | `production`, `every_stage`, `none` | `production` | `default`; `none` only `stated` |
| `deployer_roles` | a list of `{ role, scope, for }` | `[]` | `forced`, `forced_by` listing the decisions; never asked |

- `deploy_mechanism` is a `required` customer question. A run nobody can answer records an
  `open:` entry (`key: deployment.deploy_mechanism`, `owner: workload owner`,
  `blocks: apply`) and **renders no pipeline** - the reply says so. It is never `assumed`: a
  guessed pipeline is a file in the wrong directory for the wrong system.
- `local` renders a script and no pipeline; `pipeline_auth` and `pipeline_approvals` are then
  not written.
- The pipeline reads `context.environments` (the stage blocks, in order),
  `context.workload` (the state key), `deployment.stage_isolation` (one identity and one
  subscription per stage, or one subscription with role scopes), and `target`
  (Terraform plan/apply or Bicep what-if/create). Nothing about it is a resource decision, so
  none of it sits under `resources:`.
- `deployer_roles` is what the spec asks of the deploying identity beyond `Contributor` on its
  groups, re-derived on every run like any `forced` value. A `create` group adds `Contributor`
  on `subscription`; any `role_assignments` (a resource's or `wiring.`) adds `Role Based Access
  Control Administrator` on `resource_group`, conditioned to the roles the spec assigns; a key
  vault with `secret_placeholders` adds `Key Vault Secrets Officer` on that vault's key. `for`
  names the decisions behind each grant. It applies to `local` too - the person running the
  script needs the same roles. `check_spec.py` fails on a needed role that is missing.
- The platform side - identities, federated credentials, environments, approval checks,
  state account - is not in the spec. The render lists it in the pipeline's header comment,
  with `deployer_roles` as the roles beyond the baseline.

## `source` is what makes it a spec rather than a settings dump

Every value carries where it came from. Strip that field and the file degrades into a
config file whose provenance has to be guessed.

| `source` | Meaning |
|---|---|
| `stated` | The user said it in their request, before being asked |
| `asked` | The user answered it in the interview |
| `platform` | Derived from the landing-zone answers (`landing_zone_exists`, `central_*`), a platform-owned decision the customer was not asked |
| `requirement` | Derived from a customer's answer in the deployment set's `requirements` group, with `derived_from: deployment.<id>` naming it |
| `pattern` | A pattern skill pre-answered it |
| `deployment` | Inherited from the deployment set, via the question's `from_deployment` |
| `forced` | Determined by another answer, with `forced_by` naming it |
| `assumed` | The run chose a value to keep going. Valid for `plan`, never for `apply` |
| `default` | The question set's opinionated default applied |
| `carried` | Taken unchanged from a previous spec |
| `overridden` | The user contradicted a pattern pre-answer or a previous value |

`overridden` carries a comment on the same key saying what it departed from. It is the one
source that marks a deliberate exception, and an undocumented exception reads as an
accident a year later.

`assumed` and the `open:` block are the two ways a spec stays honest about what it does not
know. An `assumed` value lets a run finish and be reviewed — the alternative is no artefact
at all — but it is a placeholder with a value-shaped hole in it, so the rule is hard:
**a spec containing `assumed` renders and plans, and does not apply.** `open:` is the
list of prerequisites nothing could resolve, each with who has to answer it:

```yaml
open:
  - key: context.resource_group_name
    question: Which resource group does this deploy into?
    blocks: apply
  - key: deployment.address_space
    question: Which address range is assigned to this workload?
    owner: network / IPAM owner
    blocks: apply
```

Neither is a defect in the spec. A run that invents a resource group to avoid an empty
field is the defect, and it is invisible until someone deploys it.

`requirement` carries `derived_from`, and that is what the customer reads back: the
decision document turns `replication: ZRS, derived_from: deployment.outage_impact` into
"because an outage would be disruptive, the data is kept in three datacenters". A derived
value without its requirement is a value the customer cannot recognise as theirs.

`forced` carries `forced_by`, and that chain is the point: a Premium Key Vault is a
recurring cost, and "because the mandate requires HSM keys" is the difference between a
reviewer accepting it and reopening the decision from scratch.

```yaml
  key-vault:
    security:
      sku:
        value: premium
        source: forced
        forced_by: deployment.key_protection   # hsm, from mandate BSI C5
```

## Several of a kind

A key under `resources:` is a question set's directory name (`storage-account`). A second
resource of the same kind - an uploads account beside a host account, two App Services - takes
the set's name, two underscores and an instance name: `storage-account__host`. It reads the
questions of `storage-account`, is its own set of decisions with its own key paths
(`storage-account__host.security.min_tls_version`), and is its own entry in `composition` and
`wiring`. The first of a kind may stay unsuffixed or take an instance name too; use one style
per spec. Underscores because the key path is dot-separated and a hyphen already occurs in the
set names.

## Backend-neutral on purpose

The spec names **decisions**, not attributes. `public_network_access: disabled`, never
`public_network_access_enabled: false` — the latter is already Terraform's spelling for the
`azurerm` provider and would leak one backend's vocabulary into the interface the other
backends have to read.

The mapping from a decision to an attribute lives in the question set's `renders` field and
in each target's rendering reference. That is the layer allowed to know about
`networkAcls.defaultAction` versus `public_network_access_enabled`.

Target-specific escape hatches do exist, and are quarantined:

```yaml
resources:
  storage-account:
    _target_overrides:
      terraform:
        # Needed until azurerm supports it as a first-class argument.
        lifecycle_ignore: [tags["created_at"]]
```

Anything under `_target_overrides` needs a comment saying why, and a spec that accumulates
them is telling you the question set is missing a question.

## Modularity

`composition` is what keeps the two backends structurally comparable. Without it, each
renderer invents its own split and the same spec produces one root module in Terraform and
six Bicep files — at which point diffing the two outputs measures the renderers rather than
the decisions.

It is a decision like any other, so it carries a `source`. Usually `default`; `carried`
when an existing spec already fixed the layout; `stated` when the user asked for a
particular split.

### `granularity`

| Value | Meaning | When |
|---|---|---|
| `single` | One root, no modules | A single resource, a throwaway, or a repository that has no `modules/` |
| `per-concern` | A module per concern — the resource, its networking, its observability | Default. Mirrors the one-concern-per-file rule a level up |
| `per-resource` | A module per resource | A pattern with many resources whose parts are reused separately |
| `per-family` | A module per resource family (`network`, `security`, `ai`, ...), each holding that family's AVM calls | Default under AVM when the spec has more than one family, in both targets ([Terraform](../../iac-rendering/references/terraform-idiom.md#grouped-avm-calls-modulesfamily), [Bicep](../../iac-rendering/references/bicep-idiom.md#grouped-avm-calls-modulesfamilybicep)); the root then holds one call per family and the wiring between them |

Do not ask for it when the repository answers it. An existing `modules/` directory, or an
existing spec, decides this before the interview starts.

### A module entry

| Field | Meaning |
|---|---|
| `id` | Stable, backend-neutral. Becomes a directory in Terraform and a file in Bicep |
| `contains` | Resource keys from `resources:`, or wiring parts a pattern owns. Every resource belongs to exactly one module |
| `inputs` | Context keys and values the caller passes in. Not the full decision set — the decisions stay in `resources:` |
| `outputs` | What other modules or the caller may consume. Nothing secret |
| `needs` | Other module ids it consumes outputs from. The dependency is declared here, never discovered from the rendered code |
| `implementation` | `avm` (default), `authored`, or `reuse` — see below. Never a module path |

Three rules that hold in both targets:

- **A module never reaches into another module's resources.** It consumes a declared
  output or it does not consume it. This is enforceable in Terraform and in Bicep, and it
  is what makes `needs` the whole truth about ordering.
- **Wiring lives in the root, not in a module.** Role assignments and DNS records between
  two modules belong to whoever can see both — the same rule that makes `wiring:` a
  top-level block.
- **`needs` is acyclic.** Two modules that need each other are one module, or there is a
  wiring entry pretending to be a module.

### Reusing an existing module

Whether a module is a call to a published one or authored here is a decision, so it is in
the spec. *Which* published module, and how it is addressed, is not:

```yaml
    - id: storage
      contains: [storage-account]
      implementation: avm        # avm | authored | reuse
      source: deployment         # follows deployment.module_source unless overridden
```

| Value | Meaning |
|---|---|
| `avm` | **Default.** A call to the resource's Azure Verified Module, in whichever target renders. Follows `deployment.module_source: avm`; not written per module unless it departs |
| `authored` | Resources written out from the resource's own rendering reference. The fallback when no AVM module exists for the type — then `source: forced`, `forced_by: no AVM module for <type>` — or the deployment chose it |
| `reuse` | A published module that is not AVM, named by the user. The coordinate goes into `_target_overrides` with a comment |

The coordinate stays in the renderer, because it is target knowledge with target rules
attached — `br/public:avm/res/...` and the exact version on the Bicep side,
`Azure/avm-res-.../azurerm` and the version constraint on the Terraform side, and the
module's status in the AVM index, which decides whether it is used at all. Those belong
with [avm.md](../../iac-rendering/references/avm.md),
[bicep-idiom.md](../../iac-rendering/references/bicep-idiom.md) and
[terraform-idiom.md](../../iac-rendering/references/terraform-idiom.md), which is also where
they stay correct when a module moves or a version breaks. A spec carrying them would go
stale while looking authoritative, and would make the same decision unreadable to the
third backend.

The spec is not a lockfile either. What was actually resolved is pinned in the generated
code, which is the artefact that gets deployed and reviewed.

Two consequences worth stating before generating:

- A published module may not expose every decision the question set resolved. Name the
  ones it swallows rather than dropping them silently — that gap is the price of reuse and
  the user should see it. The rules per kind of gap are in
  [avm.md](../../iac-rendering/references/avm.md#gaps-what-the-module-does-not-carry).
- If the user named a specific module, that is a target-specific instruction and goes in
  `_target_overrides` with a comment, not into `implementation`.

### Rendering it

The spec says *what* the modules are; each target's idiom says what they look like on disk:

| | Terraform | Bicep |
|---|---|---|
| A module is | A directory, `modules/<id>/` | A file, `modules/<id>.bicep` |
| Called from | `module "<id>"` in the root | `module <id> 'modules/<id>.bicep'` |
| `needs` renders as | Passing `module.<other>.<output>` | Passing `<other>.outputs.<name>` |

Details, including the asymmetries that do not survive a naive port, are in
[terraform-idiom.md](../../iac-rendering/references/terraform-idiom.md) and [bicep-idiom.md](../../iac-rendering/references/bicep-idiom.md).

## Where it lives

The spec is source, not output. It is written into the user's repository, committed with
the code it renders, and read back by every later run. A spec that only existed in the
conversation that produced it cannot be extended: the next run would re-interview from
nothing, and the answers would drift from the code already deployed.

**One spec per deployable root**, in that root, under a fixed name:

```
infra/                       # or wherever the repository's IaC root already is
  infra-spec.yaml            # the decisions
  infra-diagram.drawio.png   # drawn from it; the PNG carries the editable diagram
  naming.yaml                # the naming convention - the customer edits it
  main.tf | main.bicep ...   # rendered from it
```

- **The repository already has an IaC root** (a directory holding `*.tf` or `main.bicep`)
  → the spec goes there. It describes that code, so it sits next to it.
- **It has none** → create `infra/` at the repository root. Say where it went; do not
  ask, since a fixed default is what lets the next run find it.
- **Several roots** (one per workload or per landing zone) → one spec in each. A spec never
  spans two roots, because `composition` and `needs` only mean something inside one.

The name is fixed — `infra-spec.yaml`, never `storage-spec.yaml` or `spec-prod.yaml` —
because finding it is the whole mechanism. Do not put it in `.gitignore`, and do not put it
under `.claude/`: it is read by reviewers and by the other backends, not only by this
plugin.

## Finding it

Before the interview, search the repository for `**/infra-spec.yaml`, skipping
`.terraform/`, `node_modules/` and `.git/`:

| Found | Then |
|---|---|
| None | A new spec. The location rule above decides where |
| One | **Extend it.** Say so in the first message — "Ich erweitere `infra/infra-spec.yaml` (storage-account, virtual-network)" — so the user can redirect if they meant something new |
| Several | Ask which one, or whether this is a new root. The paths are real, so offering them as options is fine |

Finding none while the repository holds IaC code is worth one sentence: the code was not
written from a spec, and the run that follows creates the first one beside it rather than
pretending to describe what is already there.

## Extending one

Extension is the normal case after the first run, and the spec is shaped for it: each
decision is a separate key with its own `source`, so adding to it is adding keys.

**What is carried and what is re-derived.** Values whose `source` is `stated`, `asked`,
`pattern`, `platform`, `default`, `overridden` or `carried` are carried as they are —
they were decided. Values whose `source` is `deployment`, `requirement` or `forced` are
consequences, so they are re-derived from what they follow: if `network_exposure` changes
in this run, every resource inheriting it follows; if the customer now says an outage
would be critical, every `requirement` value derived from `outage_impact` is remapped;
and every `forced` value is recomputed from its `forced_by`.

**The opening question changes.** Phase 0 asks what should be added or changed, not what is
being built — the system is already described. List what the spec holds, so the user
answers against it.

**Only the delta is asked and reported.** The deployment set is already resolved; a new
resource asks only its own surviving questions. Phase 4 shows what this run added or
changed, not the whole spec again.

| Change | In the spec |
|---|---|
| A resource added | New key under `resources:`, a `composition.modules` entry or an existing module's `contains` extended, `wiring:` entries if it connects to something |
| A decision changed | The new value with `source: overridden` and a comment naming the old value. Consequences re-derived |
| A resource removed | Its key, its `contains` entry and every `wiring:` entry naming it are deleted. Say before rendering that the plan will **destroy** it — a removal in the spec is a deletion in Azure |
| A stage added or removed | `context.environments` changes; every map gains or loses the key, a gained stage's per-stage values are asked or opened, and a removed stage's state is destroyed — say so before rendering |
| The deploy mechanism added or changed | `deployment.deploy_mechanism` with its source (`stated` when the user said it in this run). The new system's pipeline files are rendered; a replaced system's are **removed**, not left beside them - two pipelines applying one state race for its lock. Say so before rendering |
| `naming.yaml` | Carried, never regenerated. A naming change the user asks for is an edit to that file, and the plan will show it as a rename — most Azure resources cannot be renamed, so say that it destroys and recreates them |
| A question added to the set since | Absent, resolves from its default, recorded as `default`. Name the additions |

Never rewrite a value the user did not touch. Reformatting, reordering keys or
"normalising" an old answer turns the git diff of the spec — the one review this design
promises — into noise.

Update `spec.at`, `skill_version` and `generated_by` on every write; the history of the
decisions is the spec's git log, which is why it is committed.

Then regenerate both the diagram and the code from the whole spec, and let the diff show
what moved.

## Reading one back

When a spec exists, load it before interviewing. Its values enter resolution as `carried`,
so a re-run that changes nothing asks nothing.

Three cases need care:

- **`spec.plugin_version` is newer than the installed plugin.** The spec was written by a
  newer plugin, whose questions and renderings this one does not know. Nothing is asked,
  synced, rendered or written until the plugin is updated:
  `scripts/check_plugin_version.py <spec>` exits 3 for this case. A spec without the field
  predates it and is not held back. Every run that writes the spec sets the field to the
  installed version and never lowers it.
- **A question was added to the set since.** See the table above.
- **`schema_version` is older than the question set's.** Say what changed before
  regenerating. Silently migrating a file whose purpose is auditability defeats the file.

## Canonical form

The run decides; `scripts/write_spec.py` lays the file out, in place, after every write. The
same decisions then give the same file, and the git diff of a re-run shows what moved, not
how it was typed:

- the sections in the order of [Shape](#shape); a decision as `value`, `source`, then where
  it came from (`derived_from`, `forced_by`, `non_production`, `reason`);
- `deployment:` in the order of `questions/deployment.yaml`, a `# --- <group> ---` comment
  above each group (`requirements`, `posture`, ...). The comment is layout only: the key
  path stays `deployment.<id>`;
- a resource's groups and questions in the order of its question set, a blank line between
  resources. The resources keep the order the run wrote them in: the decision document, the
  name list and the picture follow it, so the part that matters most comes first;
- a decision on one line when it fits in 120 characters and holds no comment
  (`min_tls_version: {value: TLS1_2, source: default}`), likewise a short list or stage map
  (`[development, test, production]`); a longer one keeps its fields on lines of their own;
  a stage map in the order of `context.environments`; no YAML anchors;
- `spec.plugin_version` set to the installed plugin.

It changes no value and loses no comment: a comment stays at the key it stood at (a quoted
customer answer after a value, a note above a resource), and the file is written only if it
reads back the same. A comment it cannot tie to a key stops it, with the file untouched.

```powershell
python3 <plugin>/core/iac-authoring/scripts/write_spec.py ./infra-spec.yaml
# Whether a file is in canonical form, writing nothing (exit 1 when not):
python3 <plugin>/core/iac-authoring/scripts/write_spec.py ./infra-spec.yaml --check
```

`--no-stamp` lays out a spec without claiming the installed plugin made its decisions - for
a file only reformatted, never re-interviewed.

## Validate

```powershell
python3 <plugin>/core/iac-authoring/scripts/check_spec.py ./infra-spec.yaml

# Before applying, which also fails on assumed values and open entries:
python3 <plugin>/core/iac-authoring/scripts/check_spec.py ./infra-spec.yaml --require-applyable
```

Needs PyYAML (`pip install pyyaml`). Without it the script exits 2
and says so rather than reporting a file it could not read as fine.

Checks that every value carries a known `source`, that referenced skills exist, that enum
values are within the question set's `values`, that no `required` question is missing or
defaulted, and that no decision key uses a backend's attribute spelling.

For `composition`: module ids unique, every resource in `resources:` contained by exactly
one module, `contains` and `needs` pointing at things that exist, `needs` acyclic, and
`implementation` being `avm`, `authored` or `reuse` rather than a module path that belongs in the
renderer.
