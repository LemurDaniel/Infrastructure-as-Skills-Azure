# Rendering Bicep

How generated Bicep should look. Match the surrounding repository first — if it already has
a layout, follow that and ignore the defaults below.

## File layout

```
main.bicep                  # the deployment entry point
main.development.bicepparam # one file per stage in context.environments - the per-stage values
main.test.bicepparam
main.production.bicepparam
bicepconfig.json            # symbolicNameCodegen for the tests
modules/
  storage.bicep             # one resource concern per file
  storage.network.bicep     # private endpoint, DNS record
types.bicep                 # user-defined types shared across files
infra-spec.yaml
```

A `.bicepparam` file per stage beats one parameter file with conditionals inside it, and
the stage's subscription is the deployment's scope on the command line
(`az deployment group create --subscription <stage's> -g <stage's rg>`), one per stage.
Every decision whose question is `per_environment`, or whose spec value is a map keyed by
stage, is a `param` without a default whose value lives in the stage file — the address
range, the subnets, `storageSkuName` and `logRetentionDays` that `non_production_savings`
sets cheaper outside production — never a literal in the template. A stage whose values
are still `open:` gets its file with placeholders (the all-zero GUID, `OPEN-<what>`), as
in [terraform-idiom.md](terraform-idiom.md#the-context-values-and-the-stage-files); the
pipeline refuses to deploy it.
The conditionals are where environments silently diverge.

## Modules

Which files exist comes from the spec's `composition` block, not from taste — see
[spec.md](../../iac-authoring/references/spec.md). One `composition.modules` entry is one
file, named after its `id`; a
module needing its own types or several concerns becomes `modules/<id>/main.bicep` instead,
with the rest beside it.

`main.bicep` is the composition: module calls, and the wiring between them. Role
assignments and DNS records that span two modules belong there, because only the caller
can see both.

```bicep
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    environment: environment
    location: location
    workload: workload
  }
}

module storageNetwork 'modules/storage-network.bicep' = {
  name: 'storage-network'
  params: {
    // The spec's needs: [storage] — an output, never a reach into its resources.
    storageAccountId: storage.outputs.id
    subnetId: subnetId
  }
}
```

### Where Bicep modules differ from Terraform's

Four of these cost a deployment if ported naively from the Terraform side:

- **`name` is the deployment name, not a label.** It must be unique per scope per
  deployment and is capped at 64 characters. Inside a loop it needs a discriminator —
  `name: 'pep-${sub}'` — or the iterations overwrite each other's deployment and only the
  last one's outputs survive.
- **`scope:` is a module property.** Deploying into another resource group or subscription
  is `scope: resourceGroup(otherSub, otherRg)` on the module, where Terraform needs a
  provider alias passed in. This is the asymmetry that makes a cross-scope spec render
  cleanly here and awkwardly there. A split without a main group is rendered exactly so: one
  root deployed into the first group of `resource_group_split`, every module scoped to its own
  group, references between groups as module outputs
  ([resource-groups.md](resource-groups.md#what-create-changes-elsewhere)).
- **A module output is not secret.** It is readable in the deployment history, so a module
  never outputs a key or a connection string — pass a Key Vault reference instead.
- **Loops are `for`, and ordering is not an output of the loop.** `[for sub in subs: {…}]`
  on a module is fine; depending on one iteration of it is not.

`dependsOn` is almost never needed: referencing `storage.outputs.id` creates the edge.
Write it only for a dependency Bicep cannot see, with a comment saying what it is.

### Grouped AVM calls: `modules/<family>.bicep`

The Bicep counterpart of Terraform's [per-family shape](terraform-idiom.md#grouped-avm-calls-modulesfamily):
a spec with several resource families does not put dozens of AVM calls into `main.bicep`. **A local
module per family, and a `main.bicep` that only calls them and wires them.**

```
main.bicep               # one `module network 'modules/network.bicep'` per family, and the wiring
main.<stage>.bicepparam  # the stage's values
bicepconfig.json         # symbolicNameCodegen, so the tests can address resources by name
infra-spec.yaml
modules/
  network.bicep          # the family's AVM calls, its role assignments, its private endpoints
  security.bicep
  ai.bicep
tests/
  network.armtest.yaml   # this family's decisions
  security.armtest.yaml
  wiring.armtest.yaml    # what only main.bicep can see
```

Rules:

- **The family is the resource's directory under `resources/`**, as in Terraform; resources of one
  family that share a lifecycle stay together.
- **`main.bicep` is calls and wiring.** One `module <family> 'modules/<family>.bicep'` per family
  with the context values (names, ids, subnets, the stage's values) as `params`, and the role
  assignments or private links that span two families. No AVM call in it.
- **The AVM calls live in the family module**, versions pinned there, every decision written as an
  explicit literal with its `// decision:` comment, as in the AVM example above. A decision passed
  down as a `param` compiles to an expression (`[parameters('x')]`), and the test has to match text
  instead of a value - so only the **context** crosses the module boundary, not the decisions.
- **A family needing another's id takes it as a `param`**, from the other module's `output` in
  `main.bicep`; it never reaches into the other's resources.
- **`name` of a module call is the deployment name** (64 characters, unique per scope): the family
  module names its AVM deployments `'<family>-<resource>'`, so two families cannot collide.
- **Outputs are what `main.bicep` and the other families read**: ids, URIs, principal ids. Never a
  key or a connection string.

The spec carries it as `composition.granularity: per-family`, as for Terraform.

**Tests move into the family.** One `tests/<family>.armtest.yaml` per family module plus one
`tests/wiring.armtest.yaml` for `main.bicep`. `run_arm_tests.py` already reads every
`*.armtest.yaml` of the directory. A family module compiles to a nested deployment, so a decision
inside it is addressed through that deployment:

```yaml
- decision: storage-account.networking.public_network_access
  path: resources.network.properties.template.resources.storageAccount.properties.parameters.publicNetworkAccess.value
  equals: Disabled
```

`resources.<family>` is the module call in `main.bicep`, `properties.template.resources.<name>` the
symbolic resource inside it (checked against a nested compile with `symbolicNameCodegen`). What
`main.bicep` passes as a parameter is `resources.<family>.properties.parameters.<param>.value`.

### Do not generate a module per resource by reflex

`granularity: per-resource` exists for patterns whose parts are reused separately. A
one-resource module whose params restate the resource's properties is a file that adds a
hop and removes nothing. The family module is not that: it holds several AVM calls and the
decisions that belong together.

## Azure Verified Modules from the public registry

A resource renders as a call to its AVM module unless the spec says `implementation:
authored` for it — which module, which version and how the shared interfaces map is in
[avm.md](avm.md). The public registry alias `br/public:` is built into Bicep and needs no
`bicepconfig.json`; the reference is exact-versioned, always:

```bicep
// Resolved 2026-10-17 from mcr.microsoft.com; br/public takes no range, so the pin is exact.
module storageAccount 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'storage'
  params: {
    name: storageAccountName // assembled from vars, see naming.md
    location: location
    tags: tags

    // decision: storage-account.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // ...every other decision, written even where it matches the module default

    enableTelemetry: true // deployment.module_telemetry
  }
}
```

Resolving the module needs `mcr.microsoft.com` at `bicep build` time; the restored module
is cached under `~/.bicep`. An unpinned reference does not exist for `br/public`, so the
unannounced-change failure is not possible here — but a copied version string is a stale
one, so the version is looked up at render time, never recalled.

Module outputs are the wiring surface: `storageAccount.outputs.resourceId`,
`.outputs.systemAssignedMIPrincipalId`, `.outputs.privateEndpoints`. Every AVM module
outputs `resourceId` and `name`; the rest is per module and in its README.

### The owner's own registry

`implementation: reuse` — a module the user named that is not AVM — renders through the
`br/modules:` alias that the repository's `bicepconfig.json` resolves, pinned to the
version `version.json` next to the module names:

```bicep
module diagnostics 'br/modules:utility/diagnostic:1.0.0' = {
  name: 'diag-${storageAccount.name}'
  params: { /* ... */ }
}
```

Relative imports (`'../../schema/module.bicep'`) are correct **inside**
[`LemurDaniel/BICEP__Registry`](https://github.com/LemurDaniel/BICEP__Registry), where the
modules import each other, and wrong everywhere else. Generating a relative path into a
consumer repository produces a file that compiles on one machine and nowhere else.

If `bicepconfig.json` has no `br/modules` alias, do not invent one. The registry behind it
is a proof of concept and its address is not settled — writing a guessed ACR into a
consumer repository bakes in a PoC that will move. Say the alias is missing and fall back
to the AVM module or to authored code.

## Referencing a network the deployment does not own

`network_ownership: reference` in the spec means the virtual network is read, never managed.
Bicep spells that `existing`, which compiles to a reference and emits nothing into the
template's resource set:

```bicep
resource platformVnet 'Microsoft.Network/virtualNetworks@2023-11-01' existing = {
  name: vnetName
  scope: resourceGroup(networkResourceGroupName)
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' existing = {
  parent: platformVnet
  name: privateEndpointSubnetName
}
```

Note the `scope:` — a platform network usually lives in another resource group, and
without it the lookup silently targets the deployment's own and fails at resolution rather
than at compile time. By name and scope, never by a hardcoded resource id.

With `create`, the same subnet is a resource the deployment owns. Never both: two sources
of truth for one address space.

## Parameters

Every parameter carries `@description`. Constrain what the question set constrained —
`@allowed` for an `enum` question, `@minLength`/`@maxLength` for a string:

```bicep
@description('Deployment environment. Drives the rendered name, the tags and several security defaults.')
@allowed(['development', 'test', 'staging', 'production']) // keys of mappings.environment in use
param environment string

@description('Azure region. Defaults to the resource group\'s location.')
param location string = resourceGroup().location
```

Without the `@allowed`, the constraint existed only during the interview and the template
accepts anything.

Prefer a user-defined type over a long flat parameter list once a resource has more than a
handful of knobs — it keeps a resource's inputs in one shape and gives the consumer
something to read:

```bicep
@export()
type storageConfig = {
  @description('Replication. ZRS survives a zone loss at roughly LRS cost.')
  replication: 'LRS' | 'ZRS' | 'GRS' | 'GZRS'

  @description('Days blobs remain restorable after deletion. 0 disables soft delete.')
  blobSoftDeleteDays: int

  privateEndpointSubnetId: string?
}
```

### Context values are always parameters

`location`, `workload` and `resourceGroupName` are `param`s without a default, and the
subscription is the deployment's target (`az deployment group create --subscription ... -g ...`),
never a literal. Values the user stated go into the stage's `main.<stage>.bicepparam`, not
into the template.
`workload` carries `@minLength`/`@maxLength` for the name-length limit.

## Names come from vars

The registry's naming modules (`utility/naming/schema`, `utility/naming/generator`,
`genName`) are **not ready to ship** — do not import them and do not call them. On the
Bicep side the name is assembled from `var`s generated from the convention (the plugin's
`naming.default.yaml`, with the repository's `naming.yaml` merged over it when a `custom`
convention exists; a Bicep root gets no copy otherwise): its pattern for the type, its
abbreviation, its location and environment codes. See
[naming.md](naming.md) for the full pattern and the character limits that come with doing
it by hand.

```bicep
// Storage accounts: lowercase alphanumeric, no separators, max 24 characters.
var storageAccountName = toLower('st${locationCodes[location]}${environmentCodes[environment]}${workload}${padLeft(index, 2, '0')}')
```

Keep the assembly in one place per deployment and pass the finished name into modules.
Still never hardcode a literal name, and still never scatter the same interpolation across
five resources.

## Tags

One `var`, built once in `main.bicep` and passed into every module as a parameter. Never a
tag literal on a resource — it drifts from its siblings the first time the set changes.

```bicep
@description('Tags applied to every resource in this deployment.')
param tags object

// Deriving anything on top happens once, here, not per module.
var allTags = union(tags, derivedTags)
```

Which tags those are is not a rendering decision — see
[guardrails.md](../../iac-authoring/references/guardrails.md). If the deployment already
has a tags parameter or var, pass that one down instead of adding a second.

## Secure values are explicit

Write them even where they match the API default. A reviewer can see a decision that was
made; an absent property is invisible, and API defaults are not stable across versions.

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: { name: 'Standard_ZRS' }
  kind: 'StorageV2'

  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    // Access is via Entra ID and RBAC; keys would bypass both.
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}
```

### Secret placeholders: `@onlyIfNotExists()`

A Key Vault secret whose value is entered later (`secret_placeholders`, `value_source:
placeholder`) is a `Microsoft.KeyVault/vaults/secrets` resource with the `@onlyIfNotExists()`
decorator, so a redeployment never overwrites the value somebody set. Never an `if` condition
or a "seed" parameter, never a lookup of the secrets that exist, never the value as a
parameter - each of them overwrites, or leaks, on a redeployment. The full block, with its
decisions: `<plugin>/resources/security/key-vault-secret/bicep.md`.

```bicep
@onlyIfNotExists()
resource placeholder 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = [for name in secretPlaceholders: {
  parent: vault
  name: name
  properties: { value: 'placeholder - replace after deployment' }
}]
```

## API versions

Reuse the API version already used elsewhere in the repository for that resource type. A
newer version is not an improvement by itself, and a template mixing three versions of the
same type is a maintenance problem for no gain.

Never invent one. If no precedent exists in the repository, compile and let Bicep reject an
unknown version — that is a two-second check against a guess that fails at deployment.

## Outputs

Output what a consumer needs to wire against — resource id, principal id of a managed
identity, the rendered name. Never output a key, a connection string or anything else
secret: deployment outputs are readable to anyone with reader on the deployment and persist
in its history.

```bicep
output id string = storageAccount.id
output name string = storageAccount.name
output principalId string = storageAccount.identity.principalId
```

A per-instance output of a resource loop is an **array**, not a map: Bicep refuses to index
a resource loop from inside a lambda (`BCP247`), so `toObject(subs, s => s, s => pe[…].id)`
does not compile. Where Terraform renders `{ for k, pe in … : k => pe.id }`, render
`[for (sub, i) in subs: { subresource: sub, id: pe[i].id }]` and say so in the
description — it is one of the asymmetries a port has to carry rather than paper over.

## Tests

A Bicep render ships with its tests, under the same contract as Terraform's
([terraform-idiom.md](terraform-idiom.md#tests)): one assertion per spec decision, named by
its key path, or a marker with a reason for what the template cannot show. There is no
plan without a subscription, but `bicep build` is deterministic and the compiled ARM
carries every decision — as a module parameter value, or as an ARM expression whose text
still names the literal. The tests read that JSON: `tests/<name>.armtest.yaml`, run by
`scripts/run_arm_tests.py`, counted by `scripts/check_render_coverage.py`.

```yaml
- decision: storage-account.networking.public_network_access
  path: resources.storageAccount.properties.parameters.publicNetworkAccess.value
  equals: Disabled

# A value the compiler turned into an expression: match its text.
- decision: storage-account.observability.diagnostic_workspace
  path: resources.storageAccount.properties.parameters.diagnosticSettings.value[0].workspaceResourceId
  matches: "reference\\('workspace'\\)\\.outputs\\.resourceId"

# An absent block is a decision too.
- decision: storage-account.security.key_management
  path: resources.storageAccount.properties.parameters.customerManagedKey
  absent: true

- not_testable: log-analytics-workspace.data_protection.immediate_purge_protection
  reason: the forceDelete query parameter at deletion time, not a template property
```

`path` is dotted from the template root, `[n]` indexes a list; one operator per entry —
`equals`, `contains`, `matches` (a regex over the JSON text of the value) or `absent`.
`resources.<symbolicName>` needs the template compiled with symbolic names
(languageVersion 2.0): a `bicepconfig.json` beside the root with
`"experimentalFeaturesEnabled": { "symbolicNameCodegen": true }` forces it — the
Bicep roots carry one. An AVM module call compiles to a nested
deployment whose `properties.parameters.<param>.value` is the decision, which is why most
paths look alike; a loop (`for`) compiles to a `copy` whose `input` is one expression, so
the decisions inside it are matched, not equalled.

What the compiled template cannot show: a deletion-time behaviour (`forceDelete`), a
value only an output or a deployment resolves (an `existing` reference's id), a decision
recorded in the spec and rendered nowhere (`subnets_expecting_nsg`). Those are
`not_testable` with the reason, as in Terraform.

## Before handing over

```bash
bicep format main.bicep                       # or: az bicep format
bicep build --stdout main.bicep > /dev/null   # fails loudly on unknown properties
bicep build-params main.bicepparam --stdout   # the parameter file against the template
bicep lint main.bicep
python3 <plugin>/core/iac-rendering/scripts/run_arm_tests.py ./infra-spec.yaml           # tests/*.armtest.yaml against the compiled ARM
python3 <plugin>/core/iac-rendering/scripts/check_render_coverage.py ./infra-spec.yaml   # every decision asserted or marked
```

The CLI is also published as the NuGet package `Azure.Bicep.CommandLine.<rid>` — the
binary sits under `tools/` in the `.nupkg`, which is a zip. Useful where the GitHub
release download is blocked.

Then the deployment-time check, which is the one that matters:

```bash
az deployment group what-if --resource-group <rg> --template-file main.bicep --parameters main.bicepparam
```

`what-if` is Bicep's equivalent of `terraform plan`, the only step that compares against
what is deployed, and it changes nothing — it needs credentials and reader on the resource
group.

Do not report "what-if succeeded" as the result. Read it out: what is created, modified and
deleted; every replacement named with the property that forces it; which of the rest a
consumer would notice; and what `what-if` cannot see — data not migrated, a DNS record the
private endpoint needs, a role assignment that takes minutes to propagate.
