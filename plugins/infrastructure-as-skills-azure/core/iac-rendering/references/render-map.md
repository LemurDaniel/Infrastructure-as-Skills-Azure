# `render-map.yaml` - what a decision renders to

Every resource directory holds a `render-map.yaml` beside its `questions.yaml`: for each question,
the module input, provider argument or ARM property it renders to, per target and per
implementation, and the literal each answer becomes. The question set says what is decided,
backend-neutral; this file is the one place that knows how a target spells it. The rendering
references (`terraform.md`, `bicep.md`) keep what cannot be data - the call as an example,
the provider requirements, the authored blocks, the tests and the traps in prose.

`render_digest.py` prints, for each decision of a spec, the entry of the target and
implementation it renders with, filled with the spec's value. `check_render_map.py` holds
every file to the format and to its question set.

## Shape

```yaml
schema_version: 1
resource: Microsoft.Storage/storageAccounts   # the question set's `resource`

# The AVM modules per target, in the order the reference calls them. [] when the target has
# none: then the resource renders authored there and no `<target>_avm` entry is written.
modules:
  terraform: [Azure/avm-res-storage-storageaccount/azurerm]
  bicep: [avm/res/storage/storage-account]

decisions:
  networking.public_network_access:
    terraform_avm:
      attribute: public_network_access_enabled
      values: { disabled: false, enabled_with_firewall: true, enabled: true }
      also:
        enabled_with_firewall: 'network_rules = { default_action = "Deny" }'
        enabled: 'network_rules = { default_action = "Allow" }'
      note: a bool on the module, unlike the provider's string
    terraform:
      attribute: public_network_access
      values: { disabled: Disabled, enabled_with_firewall: Enabled, enabled: Enabled }
    bicep_avm:
      attribute: publicNetworkAccess
      values: { disabled: Disabled, enabled_with_firewall: Enabled, enabled: Enabled }
    bicep:
      attribute: properties.publicNetworkAccess
      values: { disabled: Disabled, enabled_with_firewall: Enabled, enabled: Enabled }

  data_protection.replication:
    terraform_avm:
      attribute: account_sku_name
      format: Standard_{value}
      note: overrides account_tier and account_replication_type - never set those beside it

  placement.environments:
    not_rendered: naming parameter `environment` and its tag; no attribute of the resource
```

## `decisions`

One key per question of the set, `<group>.<question>`, none missing and none extra. Each is
either

- **`not_rendered: <reason>`**, alone - the answer reaches no attribute (it drives naming, a
  stage list, another question), or
- **one entry per target and implementation**: `terraform` and `bicep` (authored) always,
  `terraform_avm` and `bicep_avm` exactly when `modules` lists a module for that target.

## An entry

| Field | Holds |
|---|---|
| `attribute` | The input, argument or property path the answer sets. Required unless `gap` |
| `values` | Answer -> literal, for an enum or a bool: **one key for every answer** of the question's `accepts` (or `true` and `false`). A string is a string literal - the digest quotes it for the target. An expression the target writes as code is `{ expr: '<code>' }`; `null` means the attribute or block is left out |
| `format` | A literal built from the answer, `{value}` standing for it (`Standard_{value}`). `{ expr: '{value} * 1024' }` is code, written unquoted (a unit, a duration, a list around one value). It may name other answers of the same resource as `{group.question}` - see [one literal from several answers](#one-literal-from-several-answers). Beside `values`, `{value}` is the answer's mapped fragment |
| `passthrough` | `true`: the attribute takes the answer exactly as it is (`min_tls_version = "TLS1_2"`, a bool into a bool). An enum, bool, int or string answer needs `values`, `format` or this - never nothing |
| `authored_when` | On a module (`_avm`) entry: the answers the module refuses though Azure takes them (its validation, a missing input). For one of them the resource renders authored and the spec records `implementation: authored`; the digest says so and prints the authored entry. `values` needs no literal for them. Never map such an answer to a near value - that changes the decision |
| `omit_empty` | `true`, beside `passthrough` or `format`: an empty answer (`""`, `[]`) leaves the attribute out instead of writing it empty - a free string `values` cannot key (`purview_id`, a DNS label, a fixed private IP) |
| `part_of` | `<group.question>` whose `format` names this decision: the answer is only a piece of that literal |
| `also` | Answer -> a further line the answer sets, written as code, verbatim |
| `module` | Which module carries it, when `modules` lists several for the target (plan and site), or the `companions` module an authored entry is an input of |
| `note` | One short line: the trap, the type difference, the module default that diverges |
| `gap` | The module or the provider cannot carry the decision; how it is rendered instead (an `azapi_update_resource`, an authored child). Instead of `attribute` |

**How the answer becomes the literal is always said.** A list and a reference (an answer the
render resolves to an id) pass through as they are. Every other answer says it: `values` per
answer, `format` built from it, or `passthrough: true` - which is a claim that the attribute
takes the answer's type and spelling, checked against the reference. A bool that decides
whether an id is set, a string that picks a block, a number in another unit is never a
pass-through: `vnet_integration: false` is `virtual_network_subnet_id = null`, not `= false`;
128 GB into `storage_mb` is `{ expr: '{value} * 1024' }`. Write only what the reference says -
an attribute or a literal that is not in the module README, the provider schema or the
reference is a `gap` with its reason, never a guess.

## Placeholders in code

Code - a `{ expr }` in `values` or `format`, an `also` line - names what it does not know in
one of two ways:

| Written | Means | Filled by |
|---|---|---|
| `{value}` | This decision's answer (in `format`; its mapped fragment beside `values`) | The digest |
| `{group.question}` | Another answer of the same resource (`{identity.user_assigned_identity_ids}`) | The digest, from the spec; the check fails on one that names no question of the set |
| `<name>` | What the render knows and the spec does not: a map key (`<key>`), an id from wiring or a data source, a module output | The render |

A `${...}` is the target's own interpolation and never a placeholder.

## Beyond one entry

Four shapes for resources that do not fit one module and one attribute per decision.

### A module beside the resource: `companions`

```yaml
modules:
  terraform: []                                                   # no module for the set itself
  bicep: [avm/res/compute/availability-set]
companions:
  terraform: [Azure/avm-res-compute-proximityplacementgroup/azurerm]
  bicep: [avm/res/compute/proximity-placement-group]
```

A companion is called beside the resource for a part of it (a proximity placement group, a
public IP, a WAF policy that is its own module). It does not make the `<target>_avm` entries
required; an entry - authored or `_avm` - names it with `module:` for the decisions it carries.

### One decision on several attributes or modules: a list

```yaml
  security.min_tls_version:
    terraform_avm:
      - { module: Azure/avm-res-web-site/azurerm, attribute: site_config.minimum_tls_version }
      - { module: Azure/avm-res-logic-workflow/azurerm, gap: a workflow has no TLS setting }
```

The digest prints each element. A list over several modules names the module on every
element; a list of several attributes of one call (one list answer setting three bools:
`enabled_for_deployment`, `enabled_for_disk_encryption`, `enabled_for_template_deployment`)
names none.

### One set, several resource kinds: `kinds` and `by_kind`

```yaml
kinds: { question: rule.kind }      # an enum of the set: metric | log_query | activity_log
decisions:
  rule.severity:
    terraform:
      by_kind:
        metric: { attribute: azurerm_monitor_metric_alert.severity }
        log_query: { attribute: azurerm_monitor_scheduled_query_rules_alert_v2.severity }
        activity_log: { gap: an activity log alert carries no severity }
```

`by_kind` keys are answers of the kind question; the digest picks the entry of the answer the
resource has, and says when its kind has none. An element may itself be a list.

### One literal from several answers

```yaml
  database.vcores:
    terraform_avm:
      attribute: databases.<key>.sku_name
      format: '{database.service_tier}{database.compute_tier}Gen5_{value}'
  database.service_tier:
    terraform_avm:
      attribute: databases.<key>.sku_name
      values: { general_purpose: GP_, business_critical: BC_, hyperscale: HS_ }
      part_of: database.vcores
```

A placeholder is filled with that decision's `values` literal for its answer (unquoted), else
with the answer. The decision carrying the `format` prints the whole literal; each `part_of`
decision points at it instead of printing a fragment as if it were the value.
