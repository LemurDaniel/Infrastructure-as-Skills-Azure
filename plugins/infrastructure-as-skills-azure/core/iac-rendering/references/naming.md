# Rendering names

Never hardcode a resource name. Every name comes from **one convention file**, and the two
targets read it differently:

| Target | How a name is produced |
|---|---|
| Terraform | The `LemurDaniel/naming` provider renders it, reading the repository's `naming.yaml` |
| Bicep | **Assembled from `var`s in the template**, generated from the same `naming.yaml`. The Bicep naming modules are not shipped yet |

## The mechanism

For a Terraform target `deployment.naming_source` picks what produces the names; the rest of
this file describes `provider`, the default. One mechanism per configuration, never mixed.

| `naming_source` | Rendered as |
|---|---|
| `provider` | `LemurDaniel/naming` and `data "naming_name"`, reading `naming.yaml` - [Terraform](#terraform) below |
| `module` | `module "naming" { source = "Azure/naming/azurerm" }` and its outputs (`module.naming.storage_account.name`); look up the version live and pin the minor. The module has no `naming.yaml`: a departure from its pattern is a `custom` decision, not a patch |
| `custom` | The repository's own mechanism, carried as it is - locals, an in-house module. Do not add a pattern the repository does not have |

`naming.yaml` is written for `provider` and for every Bicep root; with `module` and `custom`
the convention is the module's or the repository's own. The spec still records
`naming_convention`. Bicep ignores `naming_source`.

## The convention

[naming.default.yaml](naming.default.yaml) is the plugin's convention: the one the
`LemurDaniel/naming` provider bundles as `default` — CAF abbreviations, AVM region codes,
one pattern per type where Azure's limits demand it. It is the default the guardrails
prescribe; see [guardrails.md](../../iac-authoring/references/guardrails.md#1-naming-and-tags).

What it produces, with `location: westeurope`, `environment: production`,
`name: payments`:

| Type | Pattern | Name |
|---|---|---|
| Resource group | `<TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<INDEX>` | `rg-we-prod-payments-01` |
| Virtual network | same | `vnet-we-prod-payments-01` |
| Subnet | `<TYPE>-<ENVIRONMENT>-<NAME>-<INDEX>` | `snet-prod-payments-01` |
| Log Analytics | Azure default, `<?SUBNAME;-%s>` optional | `log-we-prod-payments-01` |
| Storage account | `<TYPE><LOCATION><ENVIRONMENT><NAME><INDEX>`, lowercase | `stweprodpayments01` |
| Key vault, Cosmos DB, Foundry, AI Search | `<TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>` | `kv-we-prod-payments-a1b2` |

### `naming.yaml` in the user's repository — a full copy, both targets

The first run writes a **full copy** of the default as `naming.yaml` next to
`infra-spec.yaml`, whatever the target. Terraform's provider reads it at plan time; Bicep's
name `var` block is generated from it. From then on that file is the user's convention:
they edit it, every later run reads it - never the plugin's default - and **no run
overwrites it**.

A full copy rather than an empty override file, for two reasons:

- **Names are part of the deployed state.** Most Azure resources cannot be renamed — a
  changed name is a destroy and a create. A convention that silently followed the plugin's
  or the provider's default would rename resources on an upgrade. The copy pins it.
- **The user can see what they are editing.** An override file of three lines hides the
  five hundred it is merged over.

**A Bicep root from before the copy** has name `var`s and no `naming.yaml`. Its first
re-render writes the copy from what the root names, not from today's default: where a
name `var` follows another pattern than the current default gives its type - the root was
rendered from an older one - that old pattern goes into the copy. The names stay, the diff
in the template is empty, and `naming_convention` stays as it was: the convention is pinned,
not changed by the customer.

When the user states a departure — a different pattern, their own abbreviation, an
environment the convention lacks — it goes **into `naming.yaml`**, never into a template
literal, and the spec records `deployment.naming_convention: custom`. A literal name in
one resource is a second convention nobody maintains.

When the repository already has a `naming.yaml`, or a provider block already pointing at
one, that file is the convention. Read it; do not replace it with the default.

### What every name needs from the spec

`<LOCATION>` is `context.location` through `mappings.location`, `<ENVIRONMENT>` is
`context.environment` through `mappings.environment`, `<NAME>` is `context.workload`.
An environment or region missing from the mappings is a render blocker, not a fallback:
add the mapping to `naming.yaml`, or ask. The environment question's values mirror the
default's `mappings.environment` for that reason.

## The resource identifier

The Terraform provider takes `<Provider>::<Namespace>/<Type>[::<kind>]`, e.g.
`Azure::Microsoft.Storage/storageAccounts`. The optional `kind` suffix selects a variant of
the same type — `Microsoft.Compute/disks::os` abbreviates to `osdisk`, `::data` to `disk`.

Each resource's `questions.yaml` states that identifier under `naming:`, alongside
the plain Bicep resource type and the **abbreviation** the Bicep vars render. Use those
rather than constructing either yourself.

## Terraform

### Use the provider, not the modules

The [`LemurDaniel/naming`](https://registry.terraform.io/providers/LemurDaniel/naming/latest)
provider supersedes the two older modules (`LemurDaniel/naming-schema/random` and
`LemurDaniel/naming/random`) — same engine, ported and tested against the modules'
fixtures, without the `module` blocks and output plumbing in between. New code uses the
provider.

The modules remain correct and are not deprecated out from under anyone. Keep using them
in a repository that already does; mixing both in one configuration only invites the
question of which one rendered a given name.

```hcl
terraform {
  required_providers {
    naming = {
      source  = "LemurDaniel/naming"
      version = "~> 1.0"
    }
  }
}

# The convention is declared once, for the whole configuration. `naming` points at
# the repository's own copy, so a provider upgrade cannot change a name.
provider "naming" {
  convention  = "default"
  naming      = "${path.module}/naming.yaml"
  # Read only by <UNIQUE_ID_n> - the key vault pattern. Key vault names are global,
  # so the seed carries the deployment scope, not just the workload.
  random_seed = "${var.subscription_id}/${var.resource_group_name}"

  parameters = {
    location    = var.location
    environment = var.environment
    name        = var.workload
  }
}

data "naming_name" "storage_account" {
  resource = "Azure::Microsoft.Storage/storageAccounts"
}

resource "azurerm_storage_account" "this" {
  name = data.naming_name.storage_account.name # stwedevmyapp01 (environment: development)
  # ...
}
```

### `naming_name` arguments

| Argument | Notes |
|---|---|
| `resource` | Required. `"Azure::<Namespace>/<Type>[::<kind>]"`. |
| `index` | `{ start, count }`. `count` is **how many names** to render, `start` only shifts the first index. |
| `naming_id` | Selects a named pattern/abbreviation variant. Takes precedence over `kind`. |
| `parameters` | Map of string, layered over the provider's `parameters`. |

Read-only: `name` (the first name), `at_index` (all of them, in index order), plus the
aliases `result` and `by_index`.

### The index trap

`index.count` is a quantity, not an upper bound, and the convention's `index_modifier`
shifts on top of `start`. With the bundled `index_modifier: 1`, `{ start = 2, count = 5 }`
renders five names numbered `03` through `07`. If you want three sequential vnets, that is
`count = 3` — not `start = 3`.

```hcl
data "naming_name" "virtual_networks" {
  resource = "Azure::Microsoft.Network/virtualNetworks"
  index    = { count = 3 }
}

resource "azurerm_virtual_network" "this" {
  count = 3
  name  = data.naming_name.virtual_networks.at_index[count.index]
  # ...
}
```

### Provider arguments

| Argument | Notes |
|---|---|
| `convention` | Bundled convention name. Defaults to `"default"` (CAF abbreviations). |
| `naming` | Path to a YAML file overriding the convention, merged per key. Always `naming.yaml` beside the spec — a full copy, see above. |
| `parameters` | `location`, `environment`, `name`, … that the patterns render from. |
| `random_seed` | Only needed if a pattern you use contains the `<UNIQUE_ID_n>` token. The same seed always resolves to the same id, so names stay stable with nothing in state. |

Everything resolves during `plan`: embedded YAML merged in memory, no API calls, nothing
persisted. That is why it is a data source rather than a resource — rendering is pure.

## Bicep

There is a naming engine in
[`LemurDaniel/BICEP__Registry`](https://github.com/LemurDaniel/BICEP__Registry/tree/master/modules/utility/naming)
under `modules/utility/naming/` (`schema` + `generator`, exporting `genName` /
`genNameId`). **Do not generate code against
it.** It is not ready to ship, and a template importing it is a template that breaks when
its interface moves. Never import `utility/naming/*`, never call `genName` or `genNameId`.

Assemble the name from `var`s instead, **generated from the convention** — the plugin's
`naming.yaml` beside the spec, the full copy above — never typed from memory, or the two
targets name the same resource differently:

- the two maps hold exactly the `mappings.location` and `mappings.environment` entries the
  deployment uses, copied from the convention;
- each name follows the pattern the convention gives its type (`patterns.Azure.<type>`,
  else `patterns.Azure.default`), with the abbreviation from `abbreviations.Azure`;
- `@allowed` on `environment` lists the keys of `mappings.environment`, so the template
  rejects what the convention cannot name.

```bicep
@allowed(['development', 'test', 'staging', 'production']) // keys of mappings.environment in use
param environment string
param location string = resourceGroup().location

@description('Workload short name, rendered into the resource name.')
param workload string

@description('Instance number, for a second instance beside the first.')
param index int = 1

// Generated from naming.yaml (mappings). Regenerate, do not edit here.
var environmentCodes = {
  development: 'dev'
  test: 'tst'
  staging: 'stg'
  production: 'prod'
}
var locationCodes = {
  westeurope: 'we'
  germanywestcentral: 'gwc'
}

var loc = locationCodes[location]
var env = environmentCodes[environment]
var idx = padLeft(index, 2, '0')

// <TYPE><LOCATION><ENVIRONMENT><NAME><INDEX>, lowercase  ->  stwedevobjects01
var storageAccountName = toLower('st${loc}${env}${workload}${idx}')

// <TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<INDEX>  ->  vnet-we-dev-objects-01
var virtualNetworkName = 'vnet-${loc}-${env}-${workload}-${idx}'

// <TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>  ->  kv-we-dev-objects-a1b2
var keyVaultName = 'kv-${loc}-${env}-${workload}-${take(uniqueString(resourceGroup().id), 4)}'
```

### The parts

| Part | Source |
|---|---|
| Abbreviation (`st`, `vnet`, `kv`, `log`, …) | `abbreviations.Azure` in `naming.yaml`; the question set's `naming.abbreviation` mirrors the default |
| Pattern | `patterns.Azure.<type>` in `naming.yaml`, else `patterns.Azure.default` |
| Location short code | `mappings.location` in `naming.yaml` |
| Environment short code | `mappings.environment` in `naming.yaml` |
| Workload | A parameter |
| Index | `padLeft(index, 2, '0')`, so `01` rather than `1` |
| `<UNIQUE_ID_n>` | `take(uniqueString(resourceGroup().id), n)` — scoped like the Terraform seed, since the names it disambiguates are global |

**`<UNIQUE_ID_n>` is the one part the targets do not share.** The provider derives it from
`random_seed`, Bicep from `uniqueString()`; the same spec therefore names a key vault
differently in Terraform and in Bicep. Say so when a spec is rendered to both, and do not
paper over it with a literal.

Declare the maps once per deployment — in `main.bicep`, or in a shared `naming.bicep`
with `@export()`ed vars if more than two modules need them — and pass the rendered name
down as a parameter rather than repeating the maps per module. When `naming.yaml` changes,
regenerate the block.

### Character rules

Nothing checks a name assembled from `var`s, so the per-type rules are the render's to keep:

- **Storage accounts, container registries**: lowercase alphanumeric only, no separators,
  3–24 characters. `toLower()` and no `-`.
- **Key vaults**: 3–24 characters, hyphens allowed, must start with a letter; with location
  and suffix that leaves 3–10 for the workload name.
- **Most others**: hyphens are conventional (`vnet-we-dev-myapp-01`).

Every resource's `bicep.md` states its own limit. If a workload name can push the rendered
name past the limit, say so rather than letting the deployment fail at creation. The
assembly stays in one `var` block per deployment, never inlined into a resource's `name:`,
so a later swap to a naming module is a change in one place.

## Names before the deploy

After the render and before the hand-over, list every resource with the name it will get.
No tool and no login can be assumed - no `terraform`, no `bicep`, no `az` - so the list is
**derived from the spec**, never read from a plan:

```powershell
python scripts/list_names.py infra-spec.yaml [--stage production] [--language de]
```

It needs the spec alone (and PyYAML): the type's pattern from the convention - the
`naming.yaml` beside the spec when there is one, else [naming.default.yaml](naming.default.yaml)
- filled from `context` (location, workload, stage), the abbreviation from the question set.
An instance (`storage-account__host`) joins the workload in `<NAME>` (`stweprodshophost01`);
`<SUBNAME>` is for sub-resources only. It lists the resource groups (a stated name verbatim,
a created one from the pattern), each resource and the vnet's subnets, per stage, and exits 1
on a name over its type's length, outside its characters, or used twice.

What it cannot know it says, per row, and the hand-over repeats it:

- **`<UNIQUE_ID_n>` is printed as `?`.** The seed (Terraform) and `uniqueString()` (Bicep)
  decide it; a key vault, Cosmos DB, Search or Foundry name is final only at the deploy.
- **A global name is never "free".** Storage, key vault, registry, App Service, Cosmos DB,
  Search and the Foundry subdomain are marked `availability unchecked`; the check needs a login.
- **Not listed:** private endpoints, diagnostic settings, role assignments and what an AVM
  module names inside itself.

Hand the list over as a table in `context.language`: resource, name, action, note. Ask once
whether the names fit ("Do the names fit?" / "Passen die Namen?"). A departure is an edit to **`naming.yaml`**
(and in Bicep the `var` block regenerated from it) with `naming_convention: custom`, then a new list; never
a literal in a template. A renamed resource is a destroy and a create - once deployed, a
name stays. The names are not a spec decision and are not written to it.
