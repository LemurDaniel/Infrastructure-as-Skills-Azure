# `infra-spec.yaml` — the handover interface

The interview does not produce code. It produces a **spec**, and the spec is what gets
rendered as Terraform or Bicep code. Keeping that boundary sharp is the most important
decision in this design. Never render code from the interview.

```
interview => spec => terraform / bicep
```

## Why a spec and not direct generation

Three things fall out of it that direct generation cannot give you:

**It is code-agnostic.** The same spec can be rendered as Terraform or as Bicep, and it
stays the record of what was decided and designed. Without a spec in the middle, each backend grows its own private notion of what was
decided, and there is nothing to compare. With one, sending a single spec through both
backends and diffing the result is a test you can actually run.

**It is reviewable at the level decisions are made.** HCL records the *result* of a
decision and never the decision itself. `public_network_access_enabled = false` tells you
the value and nothing about whether anyone chose it.

**It renders code by diffs, without reviewing the whole code base again.** The same spec always renders the same code. A change is made
in the spec - one decision added or changed - and the code is rendered again, so the git
diff shows only what that decision changed, not a rewrite of the whole code.

## Shape

```yaml
schema_version: 1

spec:
  id: payments-api
  target: terraform  # terraform | bicep
  generated_by: infrastructure-as-skills-azure
  plugin_version: 0.5.7  # the plugin that last wrote this file; an older plugin halts on it
  at: 2026-10-17T09:14:00Z

# Values every resource inherits. Resolved once, not per resource. The system is
# deployed through a stack of stages from one code base; what differs per stage is a
# map keyed by stage, rendered as a parameter whose value lives in the stage's file.
context:
  environments: [development, test, production]
  language: de  # the customer's language (en | de): the picture, the decision document, the customer-facing text
  # location, subscription_id and resource_group_name are never asked: what the request
  # states is written here, what it does not is an open: entry and a placeholder in the
  # stage file. A resource group the render creates needs no name here.
  location: westeurope
  workload: payments
  subscription_id:  # production is not known yet - see open: below
    development: 00000000-0000-0000-0000-00000000dev1
    test: 00000000-0000-0000-0000-00000000tst1
  resource_group_name:  # main exists: the platform handed the groups out
    development: rg-we-dev-payments-01
    test: rg-we-tst-payments-01
    production: rg-we-prod-payments-01
  # The tag set this repository uses, taken from it rather than prescribed here.
  tags:
    cost_center: CC-4711
    owner_team: payments

# The deployment set's answers. Resolved once; every resource inherits them.
deployment:
  # --- context ---
  stage_isolation:
    value: resource_group
    source:
      forced_by: deployment.deployment_scope
  deployment_scope:
    value: resource_group  # every group existing, the deployer's roles on its stage's groups only
    source: default
  non_production_savings:
    value: enabled
    source: default

  # --- resource_groups ---
  resource_group_layout:
    value: single  # single | split
    source: asked
  resource_groups_created:
    value: []
    source:
      forced_by: deployment.deployment_scope
  resource_lock:
    value: production
    source: default

  # --- delivery ---
  # How the code reaches Azure - see "Delivery: the pipeline" below.
  deploy_mechanism:
    value: github  # azure_devops | github | gitlab | local
    source: stated
  pipeline_auth:
    value: workload_identity  # not written when deploy_mechanism is local
    source: default
  pipeline_approvals:
    value: production  # production | every_stage | none
    source: default
  deployer_roles:  # derived, never asked: what the deploying identity needs beyond Contributor
    value:
    - role: Role Based Access Control Administrator
      scope: resource_group
      for: [wiring.role_assignments]
    - role: Key Vault Secrets Officer
      scope: key-vault
      for: [resources.key-vault.security.secret_placeholders]
    source:
      forced_by: [wiring.role_assignments, resources.key-vault.security.secret_placeholders]

  # --- requirements ---
  network_requirements:
    value: assigned_ranges
    source: asked
  outage_impact:
    value: disruptive
    source: asked

  # --- modules ---
  module_source:
    value: avm
    source: asked
  module_telemetry:
    value: disabled
    source: default

  # --- posture ---
  network_exposure:
    value: private
    source: asked
  local_auth:
    value: disabled
    source: default

  # --- compliance ---
  mandates:
    value: [BSI C5]
    source: stated
  key_protection:
    value: hsm
    source: stated
    forces: [resources.key-vault.vault.sku]  # what this answer determined elsewhere

  # --- network ---
  network_ownership:
    value: create
    source: default
  address_space:
    # per_environment: one value per stage, never a literal in the template. A stage
    # nobody could answer for is missing here and named in open: below.
    value:
      development: 10.42.0.0/24
      test: 10.43.0.0/24
      production: 10.44.0.0/24
    source: asked
  private_endpoint_subnet_prefix:
    value:
      development: 10.42.0.0/27
      test: 10.43.0.0/27
      production: 10.44.0.0/27
    source: asked

  # --- dns ---
  private_dns_ownership:
    value: platform
    source: default

  # --- observability ---
  observability_ownership:
    value: none
    source: asked

# The split of the rendered code into modules: which module holds which resources, what
# it takes in and gives out, and which other modules it needs. Decided once here, so
# Terraform and Bicep render the same modules.
composition:
  granularity: per-family  # single | per-concern | per-resource | per-family
  source: default
  modules:
  - id: network
    contains: [virtual-network]
    inputs: [environment, location, workload, resource_group_name]
    outputs: [id, private_endpoint_subnet_id, integration_subnet_id]
  - id: compute
    contains: [app-service]
    needs: [network]  # consumes network.integration_subnet_id
    inputs: [environment, location, workload, resource_group_name]
    outputs: [id, principal_id]
  - id: storage
    contains: [storage-account]
    needs: [network]
    inputs: [environment, location, workload, resource_group_name]
    outputs: [id, name]
  - id: security
    contains: [key-vault]
    needs: [network]
    inputs: [environment, location, workload, resource_group_name]
    outputs: [id, uri]

# Every resource's decisions, under the groups of its question set. `meta` comes first and
# describes rather than decides: what the resource is for, in the customer's words.
resources:
  virtual-network:
    addressing:
      address_space:
        value:
          development: 10.42.0.0/24
          test: 10.43.0.0/24
          production: 10.44.0.0/24
        source: deployment
      subnets:
        value:
          development:
          - name: snet-app
            prefix: 10.42.0.64/26
          test:
          - name: snet-app
            prefix: 10.43.0.64/26
          production:
          - name: snet-app
            prefix: 10.44.0.64/26
        source: asked
      private_endpoint_subnet_prefix:
        value:
          development: 10.42.0.0/27
          test: 10.43.0.0/27
          production: 10.44.0.0/27
        source: deployment

  app-service:
    meta:
      purpose:
        value: Zahlungs-API
        source: stated
    hosting:
      sku:
        value:
          development: B1
          test: B1
          production: P1v3
        source: default
    networking:
      public_network_access:
        value: disabled
        source: deployment
      integration_subnet:
        value:  # a reference: a part of a resource of this spec, the same in every stage
          resource: virtual-network
          part: snet-app
        source: stated
    identity:
      managed_identity:
        value: system_assigned
        source: default

  storage-account:
    meta:
      purpose:
        value: Belege
        source: stated
    networking:
      public_network_access:
        value: disabled
        source: deployment
    security:
      shared_access_key_enabled:
        value: false
        source: deployment
      min_tls_version:
        value: TLS1_2
        source: default
    data_protection:
      replication:
        value:
          development: LRS
          test: LRS
          production: ZRS
        source:
          derived_from: deployment.outage_impact
      blob_soft_delete_days:
        value: 7
        source: default

  key-vault:
    meta:
      purpose:
        value: API-Schlüssel
        source: stated
    vault:
      sku:
        value: premium
        source:  # hsm, from mandate BSI C5
          forced_by: deployment.key_protection
    networking:
      public_network_access:
        value: disabled
        source: deployment
    security:
      secret_placeholders:
        value: [payment-api-key]
        source: stated

# Decisions that belong to no single resource; the root holds them.
wiring:
  # Which zone belongs to which endpoint: iac-rendering/references/private-dns-zones.md
  private_dns_zones:
    value: [privatelink.blob.core.windows.net, privatelink.vaultcore.azure.net]
    source:
      forced_by: deployment.network_exposure
  role_assignments:
    value:
    - from: app-service
      to: storage-account
      role: Storage Blob Data Contributor
    - from: app-service
      to: key-vault
      role: Key Vault Secrets User
    source: stated
  # Read by the diagram (core/iac-diagram): who reaches what. `from`/`to` are resource keys
  # or actors (internet, users, external:<name>).
  access:
    value:
    - from: users
      to: app-service
      label: HTTPS 443
    - from: app-service
      to: storage-account
    - from: app-service
      to: key-vault
    source: stated

# What nothing could resolve, each with who has to answer it. Applying waits for it.
open:
- key: context.subscription_id
  environments: [production]
  question: In welche Subscription wird die Produktion ausgerollt?
  owner: Plattform-Team
  blocks: apply
```

## The head and the context

| Key | Holds |
|---|---|
| `schema_version` | The version of this file's format, an integer: `1`. Not the question sets' `schema_version`, which versions their format and moves on its own. `check_spec.py` fails on a version newer than the plugin reads |
| `spec.id` | The root's name, stable across runs; lower case and hyphens |
| `spec.target` | `terraform` or `bicep` |
| `spec.generated_by` | `infrastructure-as-skills-azure`: what wrote the file |
| `spec.plugin_version` | The plugin version that last wrote it; set by `write_spec.py`, never lowered (see *Reading one back*) |
| `spec.at` | When it was last written, UTC, ISO 8601 (`2026-10-17T09:14:00Z`); the decision document prints its date |
| `context.environments` | The stages, in deployment order (see *Stages*) |
| `context.language` | The customer's language (see *Language*) |
| `context.location` | The region; a value or an `open:` entry, never picked by the run |
| `context.workload` | The workload's short name; the naming interface and the state key read it |
| `context.subscription_id` | A stage map; a stage nobody named is an `open:` entry |
| `context.resource_group_name` | The main group of a single layout, a stage map (see *Resource groups*) |
| `context.tags` | A flat map of tag name to value, taken from the repository or the request - the plugin prescribes none ([guardrails.md](guardrails.md#1-naming-and-tags)). Every resource gets it; absent or empty renders an empty set |

## Language

`context.language` is the customer's language, `en` or `de`: the fixed labels of the picture,
the decision document and every customer-facing text in the spec (`meta.purpose`,
`wiring.access[].label`, the `owner` and `question` of an `open:` entry) are written in it.
Phase 0 sets it from the language the request and the answers are written in; it is never
asked. The scripts read it (`new_diagram.py`, `verify_diagram.py`, `export_decisions.py`) and
their `--language` only overrides it for a check. A spec without it is drawn in English and
`check_spec.py` warns. Keys, values, `why` and `reason` stay English whatever it says.

## Stages: one value or a map

`context.environments` lists the stages the code is deployed through — `[development,
test, production]` by default, `[sandbox]` for one throwaway environment. Every value in
the spec is then either **one value for every stage** (a scalar, a list, a reference) or
**a map keyed by stage**:

```yaml
      min_tls_version:  # one value: a literal in the template, the same in every stage
        value: TLS1_2
        source: default
      replication:      # a map: a parameter, each stage's value in its stage file
        value:
          development: LRS
          test: LRS
          production: ZRS
        source:
          derived_from: deployment.outage_impact
```

When a map, when one value:

- **Always a map:** a `per_environment` value from outside the spec - an address range, a
  subscription, a name. Even when every stage has the same value: one value would end up
  hard-coded in the template.
- **One value:** a reference (see *References* below) and `[]`. A reference to an existing
  resource carries its per-stage ids inside it.
- **A map if a stage departs:** a cost knob that takes its cheaper `non_production_default`
  outside production, or a departure the user named for one stage (`{ overridden: <reason> }`).
- **Never a map:** everything else. A posture holds for the whole system.

`check_spec.py` enforces all four. A map's keys are stages of `context.environments`.

The renderer reads a map as a parameter and writes each stage's value into that stage's
parameter file; one value is a literal in the template.

Which stages took the cheaper `non_production_default` is not recorded: it follows from the
question, `deployment.non_production_savings` and the values, and the decision document
derives it from them. A stage the user set differently says so in the source.

### A stage nobody could answer for

A stage missing from a map is not guessed. It is an `open:` entry that names the stage:

```yaml
open:
  - key: deployment.address_space
    environments: [test, production]
    question: Which address ranges are assigned to the test and production stages?
    owner: network / IPAM owner
    blocks: apply
```

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

## References

A question with `accepts: { ref: <kind> }` (question-set-format.md) points at another
resource. Its value takes one of two forms, and nothing else - no bare name, no stage map
around it, no name and resource group:

```yaml
      integration_subnet:          # a resource of this spec: one value, every stage
        value:
          resource: virtual-network
          part: snet-app           # where the kind is a part of the resource (a subnet)
        source: stated
  diagnostics_destination:         # one outside it, its id known: the id per stage
    value:
      existing: log_analytics_workspace
      id:
        development: /subscriptions/<sub>/resourceGroups/rg-mgmt-dev/providers/Microsoft.OperationalInsights/workspaces/law-dev
        test: /subscriptions/<sub>/resourceGroups/rg-mgmt-tst/providers/Microsoft.OperationalInsights/workspaces/law-tst
        production: /subscriptions/<sub>/resourceGroups/rg-mgmt-prod/providers/Microsoft.OperationalInsights/workspaces/law-prod
    source: platform
```

- **`resource:`** names a resource key of this spec whose question set creates that kind;
  `part:` names the part where the kind is one (a subnet in the network's `subnets`, an event
  hub, a backend pool). The render takes the id from the resource's module, per stage.
- **`existing:`** names the kind of a resource outside the spec - the platform's workspace, a
  hub subnet, a key the security team holds. The render never looks it up (no data source:
  name and group are as unknown as the id, and `plan` would need read access to the platform):
  it becomes an id parameter (`variable` / `param`) filled from each stage file. The spec
  carries the id, never a name or a resource group. An id the person names goes into `id:`
  per stage; without one, `{ existing: <kind> }` stands alone and an `open:` entry with its
  owner names the key - the stage file gets a placeholder, `plan` and the tests run, the
  pipeline refuses `apply`, and answering the entry is an edit of the stage files, no
  re-render. A stage whose id is still missing is named by an `open:` entry with
  `environments:`. A property the input
  needs that the id does not carry (a connection string, a principal id, a host name) is a
  second parameter from the stage file, never in the spec: the `open:` entry asks for it,
  with the id or alone.

What each kind is - the sets that create it, the part, the ARM type its id carries, the id's
form (`arm`, `arm_any`, `guid`) - is [ref-kinds.yaml](ref-kinds.yaml); `check_spec.py` reads it
for every reference (`scripts/spec_ref.py`).

## Resource groups: roles, modes, names

`context.resource_group_name` is the **main** group of a single layout: one group per stage that
holds everything. A split has no main group - every resource is in the group of its scheme's
role, and the Bicep root deploys into the first of them. **Which groups exist is not written
down:** every role a resource is in gets one, derived from the scheme, the role table and the
placements. A group the person does not want goes by moving its resources elsewhere
(`placement.resource_group`). Splitting is a deployment decision; the keys it leaves in the spec:

| Key | Holds | Notes |
|---|---|---|
| `deployment.deployment_scope` | `resource_group` or `subscription` - asked in Phase 0, right after the module choice | `resource_group`: every group `existing`, `resource_groups_created` not asked. `stage_isolation` follows it (`source: { forced_by: deployment.deployment_scope }`) |
| `deployment.resource_group_layout` + `deployment.resource_group_scheme` | `single`, or `split` with a scheme: `concern` (`network`, `data`, `application`, `observability`, `security`), `lifecycle` (`foundation`, `state`, `runtime`), `protection` (`protected`, `standard`), `component` (`shared` and the parts) | Asked as two questions: one group or several, then how - five options do not fit one question. `single` or absent: one group, no scheme, nothing below is written. A split without a scheme means `concern`, which is what a spec written before the key holds |
| `deployment.resource_groups_created` | The groups the render creates: `main` under `single`, groups of the split under `split` - asked under `deployment_scope: subscription` | **The one record of it:** a group on the list is created, every other one exists beforehand; no mode per group is written. `[]` by default. Not asked, and `[]`, under `deployment_scope: resource_group` |
| `deployment.resource_group_lock` | `production`, `all_stages`, `none` | Only groups the render creates get a lock |
| `deployment.resource_lock` | `production`, `all_stages`, `none` | A `CanNotDelete` lock on each resource that holds data or state, in the stages named; see [avm.md](../../iac-rendering/references/avm.md#the-shared-interfaces) for which kinds |
| `context.resource_group_name_<role>` | The name of the group, a stage map like `resource_group_name` | `main` keeps `context.resource_group_name`, which a split does not write. Optional, like it: recorded when the customer or the platform stated it, otherwise a parameter the stage file supplies. For a `create` group a stated name is used verbatim; without one the render computes it from the naming interface. Never for a role no resource is in |
| `resources.<key>.placement.resource_group` | One role, for a resource that departs from its kind's role | `source: { overridden: <reason> }`; without the key the kind's role applies |
| `resources.<key>.placement.location` | One region, for the Foundry account only, when `context.location` does not offer a model | A departure the person names: `source: { overridden: <the model> }`; the same in every stage; refused under `data_residency: country`. Without the key the account runs in `context.location` |

```yaml
context:
  # No resource_group_name: a split has no main group. The created groups' names are
  # computed by the render; only the existing one is named.
  resource_group_name_network:  # network exists: the platform handed it out
    production: rg-spoke-chatbot-prod-we
deployment:
  deployment_scope:
    value: subscription
    source: asked
  resource_group_layout:
    value: split
    source: asked
  resource_group_scheme:
    value: concern
    source: asked
  resource_groups_created:  # network is not on it: it exists
    value: [data, application]
    source: asked
resources:
  storage-account__host:
    placement:
      resource_group:
        value: application
        source:
          overridden: The Function App's own state lives and goes with the app, not with the data.
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
- **Resource-group scope creates nothing.** Under `deployment.deployment_scope:
  resource_group` (and the `stage_isolation: resource_group` it derives)
  `resource_groups_created` is `[]` (`source: { forced_by: deployment.deployment_scope }`)
  and no deployer role is scoped to `subscription`: a role on the subscription reaches every
  stage in it. Each stage's identity holds its roles on its own
  groups; `check_spec.py` fails on either breach.
- **A group put on or taken off `resource_groups_created` is not an edit of a value.** It
  creates, deletes or orphans a real group; the next run says so before it writes, and the pipeline refuses a Terraform plan
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
| `deployer_roles` | a list of `{ role, scope, for }` | `[]` | `{ forced_by: [...] }` listing the decisions; never asked |

**Which system.** `deploy_mechanism` is a `required` customer question and never `assumed`: a
guessed pipeline is a file in the wrong directory for the wrong system. If nobody can answer
it, the spec gets an `open:` entry (`key: deployment.deploy_mechanism`, `owner: workload
owner`, `blocks: apply`), no pipeline is rendered, and the reply says so. `local` renders a
deploy script instead of a pipeline; `pipeline_auth` and `pipeline_approvals` are then not
written.

**What else the pipeline reads.** No key of its own beyond the four - it takes the rest from
the spec:

| Key | Gives the pipeline |
|---|---|
| `context.environments` | The stage blocks, in order |
| `context.workload` | The state key |
| `deployment.stage_isolation` | One identity and subscription per stage, or one subscription with role scopes |
| `spec.target` | Terraform plan/apply, or Bicep what-if/create |

**What the deploying identity needs.** `deployer_roles` lists the roles beyond `Contributor`
on its groups. It is derived, never asked, and recomputed on every run:

| When the spec has | The identity needs |
|---|---|
| A group in `resource_groups_created` | `Contributor` on the subscription |
| Any `role_assignments` (a resource's or `wiring.`) | `Role Based Access Control Administrator` on the resource group, limited to the roles the spec assigns |
| A key vault with `secret_placeholders` | `Key Vault Secrets Officer` on that vault |

`for` names the decisions behind each grant. The same holds for `local` - whoever runs the
script needs the same roles. `check_spec.py` fails when a needed role is missing.

**What is not in the spec.** The platform side - identities, federated credentials, pipeline
environments, approval checks, the state storage account. The render lists it in the
pipeline's header comment, `deployer_roles` included.

## `source` is what makes it a spec rather than a settings dump

Every value carries where it came from. Strip that field and the file degrades into a
config file whose provenance has to be guessed.

`source` is a word, or - where the origin points at something - a map of one key that says
both what kind of source it is and where it points:

| `source` | Meaning |
|---|---|
| `stated` | The user said it in their request, before being asked |
| `asked` | The user answered it in the interview |
| `platform` | Derived from the landing-zone answers (`landing_zone_exists`, `central_*`), a platform-owned decision the customer was not asked |
| `pattern` | A pattern skill pre-answered it |
| `deployment` | Inherited from the deployment set, via the question's `answer: { deployment: <id> }` |
| `default` | The question set's opinionated default applied |
| `carried` | Taken from what the repository already holds without a spec - an existing pipeline, an existing `modules/` layout. A value of this spec keeps its own source on a re-run |
| `assumed` | The run chose a value to keep going. Rendered as a stage-file parameter marked `ASSUMED:`: valid for `plan`, refused by the pipeline for `apply` |
| `{ derived_from: deployment.<id> }` | A requirement: mapped from a customer's answer in the deployment set's `requirements` group |
| `{ forced_by: <key> }` | Forced: determined by another answer; a list where several did |
| `{ overridden: <reason> }` | The user departed from a default, a derived value or a previous answer, and why |

Nothing else sits beside `value` and `source` but `forces` (a note naming what this answer
determined elsewhere). `check_spec.py` fails on a pointer written beside the source
(`forced_by:`, `reason:`), on `forced`, `requirement` or `overridden` written as a word, and
on `non_production`, which is derived.

An override carries its reason. It is the one source that marks a deliberate exception, and
an undocumented exception reads as an accident a year later; `check_spec.py` fails on one
without it.

`assumed` and the `open:` block are the two ways a spec stays honest about what it does not
know. An `assumed` value lets a run finish and be reviewed — the alternative is no artefact
at all — but it is a placeholder with a value-shaped hole in it, so the rule is hard:
**a spec containing `assumed` renders and plans, and does not apply.** The render puts the
value into every stage file with an `ASSUMED:` marker, and the pipeline refuses a file that
holds one, as it refuses an open placeholder. `open:` is the
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

| Field | Holds |
|---|---|
| `key` | Required. The key path the entry stands for (`context.subscription_id`, `deployment.address_space`, `resources.<key>.<group>.<id>`) |
| `environments` | The stages still missing, where the value is a stage map; absent means every stage |
| `question` | What has to be answered, in `context.language` |
| `owner` | Who answers it, in `context.language` (`Plattform-Team`, `network / IPAM owner`); absent when the person asking is the one to answer |
| `blocks` | Required. The first step it stops: `render` - the part is not rendered until it is answered (nothing to render it from); `plan` - rendered, but `plan` cannot run on a placeholder; `apply` - rendered and planned with a placeholder in the stage file, the pipeline refuses `apply`. Most entries are `apply`: the placeholder exists so that everything before it runs |

Neither is a defect in the spec. A run that invents a resource group to avoid an empty
field is the defect, and it is invisible until someone deploys it.

A requirement names the answer it came from, and that is what the customer reads back: the
decision document turns `replication: ZRS, source: { derived_from: deployment.outage_impact }` into
"because an outage would be disruptive, the data is kept in three datacenters". A derived
value without its requirement is a value the customer cannot recognise as theirs.

A forced value names what forced it, and that chain is the point: a Premium Key Vault is a
recurring cost, and "because the mandate requires HSM keys" is the difference between a
reviewer accepting it and reopening the decision from scratch.

```yaml
  key-vault:
    vault:
      sku:
        value: premium
        source:
          forced_by: deployment.key_protection  # hsm, from mandate BSI C5
```

## `meta`: what a resource is for

`resources.<key>.meta` holds what describes a resource rather than decides it, and no
question set asks it. Today that is `purpose`: a few words in the customer's language
(`context.language`), for a resource whose purpose the request says - the picture prints it
under the type (`Storage Account · Belege`), and the `component` resource-group scheme
derives its parts from it
(`source: { forced_by: meta.purpose }`). A resource the request names without saying what it
is for gets none, never a restatement of its type. `meta` is written first in a resource,
before the groups of its set.

```yaml
resources:
  storage-account:
    meta:
      purpose:
        value: Belege
        source: stated
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

The mapping from a decision to an attribute and its literal lives in the resource's
`render-map.yaml` and in each target's rendering reference. That is the layer allowed to know about
`networkAcls.defaultAction` versus `public_network_access_enabled`.

Target-specific escape hatches do exist, and are quarantined:

```yaml
resources:
  storage-account:
    _target_overrides:
      terraform:
        lifecycle_ignore:
          value: [tags["created_at"]]
          reason: Needed until azurerm supports it as a first-class argument.
```

`_target_overrides` sits on a resource or at the top level, keyed by target (`terraform`,
`bicep`); each override is `{ value, reason }` and nothing else. The reason is data, not a
YAML comment: the render reads the spec through a parser, which drops comments, and writes
the reason as the comment above the code it produces. `check_spec.py` fails on an override
without one. A spec that accumulates overrides is telling you the question set is missing a
question.

## Modularity

`composition` is what keeps the two backends structurally comparable. Without it, each
renderer invents its own split and the same spec produces one root module in Terraform and
six Bicep files — at which point diffing the two outputs measures the renderers rather than
the decisions.

It is a decision like any other, so it carries a `source`. Usually `default`; `carried`
when an existing `modules/` directory fixed the layout; `stated` when the user asked for a
particular split. An existing spec's `composition` is kept with the source it has.

### `granularity`

| Value | Meaning | When |
|---|---|---|
| `single` | One root, no modules | A single resource, a throwaway, or a repository that has no `modules/` |
| `per-concern` | A module per concern — the resource, its networking, its observability | Default for authored code, or AVM with one family. Mirrors the one-concern-per-file rule a level up |
| `per-resource` | A module per resource | Many resources whose parts are reused separately |
| `per-family` | A module per resource family (`network`, `security`, `ai`, ...), each holding that family's AVM calls | Default under AVM when the spec has more than one family, in both targets ([Terraform](../../iac-rendering/references/terraform-idiom.md#grouped-avm-calls-modulesfamily), [Bicep](../../iac-rendering/references/bicep-idiom.md#grouped-avm-calls-modulesfamilybicep)); the root then holds one call per family and the wiring between them |

Do not ask for it when the repository answers it. An existing `modules/` directory, or an
existing spec, decides this before the interview starts.

### A module entry

| Field | Meaning |
|---|---|
| `id` | Stable, backend-neutral. Becomes a directory in Terraform and a file in Bicep |
| `contains` | Resource keys from `resources:`. Every resource belongs to exactly one module |
| `inputs` | Context keys and values the caller passes in. Not the full decision set — the decisions stay in `resources:` |
| `outputs` | What other modules or the caller may consume. Nothing secret |
| `needs` | Other module ids it consumes outputs from. The dependency is declared here, never discovered from the rendered code |
| `implementation` | `avm` (default), `authored`, or `reuse` — see below. Never a module path. Written only where it departs from `deployment.module_source` |
| `source` | Beside `implementation`, where the departure came from: `{ forced_by: ... }` or `{ overridden: <reason> }` |

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
    - id: storage                # follows deployment.module_source: avm - nothing written
      contains: [storage-account]
    - id: container
      contains: [container-apps]
      implementation: authored   # avm | authored | reuse - written where it departs
      source:
        overridden: The repository's container module is authored; this one joins it.
```

| Value | Meaning |
|---|---|
| `avm` | **Default.** A call to the resource's Azure Verified Module, in whichever target renders. Follows `deployment.module_source: avm`; not written per module unless it departs |
| `authored` | Resources written out from the resource's own rendering reference. The fallback when no AVM module exists for the type — then `source: { forced_by: no AVM module for <type> }` — or the deployment chose it |
| `reuse` | A published module that is not AVM, named by the user. The coordinate goes into `_target_overrides` with its reason |

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
  `_target_overrides` with its reason, not into `implementation`.

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
`pattern`, `platform`, `default`, `carried` or `{ overridden }` are kept as they are, source
included — they were decided, and `asked` read back as `carried` would lose who decided.
Values whose source is `deployment`, `{ derived_from }` or `{ forced_by }` are consequences,
so they are re-derived from what they follow: if `network_exposure` changes in this run,
every resource inheriting it follows; if the customer now says an outage would be critical,
every value derived from `outage_impact` is remapped; and every forced value is recomputed
from what forced it.

**The opening question changes.** Phase 0 asks what should be added or changed, not what is
being built — the system is already described. List what the spec holds, so the user
answers against it.

**Only the delta is asked and reported.** The deployment set is already resolved; a new
resource asks only its own surviving questions. Phase 4 shows what this run added or
changed, not the whole spec again.

| Change | In the spec |
|---|---|
| A resource added | New key under `resources:`, a `composition.modules` entry or an existing module's `contains` extended, `wiring:` entries if it connects to something |
| A decision changed | The new value with `source: { overridden: <reason> }`, the reason naming the old value. Consequences re-derived |
| A resource removed | Its key, its `contains` entry and every `wiring:` entry naming it are deleted. Say before rendering that the plan will **destroy** it — a removal in the spec is a deletion in Azure |
| A stage added or removed | `context.environments` changes; every map gains or loses the key, a gained stage's per-stage values are asked or opened, and a removed stage's state is destroyed — say so before rendering |
| The deploy mechanism added or changed | `deployment.deploy_mechanism` with its source (`stated` when the user said it in this run). The new system's pipeline files are rendered; a replaced system's are **removed**, not left beside them - two pipelines applying one state race for its lock. Say so before rendering |
| `naming.yaml` | Carried, never regenerated. A naming change the user asks for is an edit to that file, and the plan will show it as a rename — most Azure resources cannot be renamed, so say that it destroys and recreates them |
| A question added to the set since | Absent, resolves from its default, recorded as `default`. Name the additions |

Never rewrite a value the user did not touch. Reformatting, reordering keys or
"normalising" an old answer turns the git diff of the spec — the one review this design
promises — into noise.

Update `spec.at` and `generated_by` on every write; `write_spec.py` sets
`spec.plugin_version`. The history of the decisions is the
spec's git log, which is why it is committed.

Then regenerate both the diagram and the code from the whole spec, and let the diff show
what moved.

## Reading one back

When a spec exists, load it before interviewing. Its values enter resolution as decided,
each with the source it has, so a re-run that changes nothing asks nothing and writes
nothing new.

Three cases need care:

- **`spec.plugin_version` is newer than the installed plugin.** The spec was written by a
  newer plugin, whose questions and renderings this one does not know. Nothing is asked,
  synced, rendered or written until the plugin is updated:
  `scripts/check_plugin_version.py <spec>` exits 3 for this case. A spec without the field
  predates it and is not held back. Every run that writes the spec sets the field to the
  installed version and never lowers it.
- **A question was added to the set since.** See the table above.
- **`schema_version` differs from the spec format this plugin writes** (`1`). Newer: the
  file is in a format this plugin does not know - `check_spec.py` fails, and nothing is
  written until the plugin is updated. Older: say what changed before regenerating. Silently
  migrating a file whose purpose is auditability defeats the file. The question sets'
  `schema_version` plays no part here.

## Canonical form

The run decides; `scripts/write_spec.py` lays the file out, in place, after every write. The
same decisions then give the same file, and the git diff of a re-run shows what moved, not
how it was typed:

- the sections in the order of [Shape](#shape), `open:` last; a decision as `value`, `source`, then `forces` - the
  decisions this answer determined elsewhere, a note for the reader; the checks read the
  `forced_by` on the other side;
- `deployment:` in the order of `questions/deployment.yaml`, a `# --- <group> ---` comment
  above each group (`requirements`, `posture`, ...). The comment is layout only: the key
  path stays `deployment.<id>`;
- a resource's groups and questions in the order of its question set, a blank line between
  resources. The resources keep the order the run wrote them in: the decision document, the
  name list and the picture follow it, so the part that matters most comes first;
- every map in block style, one key per line - a decision, a stage map (in the order of
  `context.environments`), a source, an item of a list - so every key reads down the page at
  its own indent; only a short list of plain values stays on one line
  (`[development, test, production]`); no YAML anchors;
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

What it checks is the contract of this file: provenance (a known `source`, an override with
its reason, a `forced_by` that exists, a `derived_from` naming a deployment answer), the
key paths and enum values against the question sets, no backend attribute spelling,
`composition`, stage maps, resource groups and their modes, the context a stage file needs,
`deployer_roles` and the shape of `wiring.access`. The numbered list in the script's
docstring is the complete one; it is kept there so it cannot drift from the code.

The Shape example above is tested: `tests/run_spec_tests.py` lifts it out of this file and
fails unless `check_spec.py` passes it and `write_spec.py --check` finds it canonical.
