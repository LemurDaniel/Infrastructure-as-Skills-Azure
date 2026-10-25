# Azure storage

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Each resource is a directory holding its question set, notes and both renderings;
this file routes to the right one and holds what is true across the family.

## Pick the question set

| Request mentions | Question set | Notes |
|---|---|---|
| storage account, blob storage, ADLS Gen2, data lake, static website | `storage-account/questions.yaml` | [notes](storage-account/notes.md) |
| container, blob container | `blob-container/questions.yaml` | [notes](blob-container/notes.md) - a child of an account; resolve the account first; an encryption scope is set with its lock or not at all |
| file share, Azure Files, SMB share, NFS share | `file-share/questions.yaml` | [notes](file-share/notes.md) - needs an account of the right kind; shared keys off changes how it mounts |
| queue, storage queue | `queue/questions.yaml` | [notes](queue/notes.md) - not Service Bus; the set asks whether ordering or a dead-letter queue is needed |
| table, Table storage | *not yet written* | - |

When a question set does not exist yet, say so rather than improvising one. Generating a
resource without its decision set is how this plugin loses the property that makes it worth
using. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) — the interview protocol: resolution
   order, what gets asked, the spec, and
   [references/guardrails.md](../../core/iac-authoring/references/guardrails.md) for where
   the defaults come from
2. [iac-rendering](../../core/iac-rendering/SKILL.md) — the spec into Terraform or Bicep,
   plus `<resource>/terraform.md` or `<resource>/bicep.md` for this resource's
   specifics, and the validate step at the end of each idiom file

## True for the whole family

**The portal defaults are permissive and the guardrail defaults are not.** Public network
access, shared-key auth and anonymous blob access all ship enabled on a storage account.
The question sets invert all three. Expect that to surprise someone who has only created
accounts in the portal — say what you changed rather than letting them discover it.

**Data-plane objects are a separate decision from the account.** A container, share or
queue inherits the account's network posture and auth model and cannot soften it. If a
request mixes both — "ein Storage Account mit einem Container für Uploads" — resolve the
account first, then the child, and keep them in separate files so the account's lifecycle
is not tied to a container's.

**A container's encryption scope is both properties or neither.** `defaultEncryptionScope` and
`denyEncryptionScopeOverride` (Terraform: `default_encryption_scope` and
`deny_encryption_scope_override`) are sent together; Azure refuses a container that carries one
without the other (`ContainerOperationFailure`, missing `x-ms-default-encryption-scope` or
`x-ms-deny-encryption-scope-override`). With no scope set - `encryption_scope_locked: false` is
the default - the render writes neither, never `denyEncryptionScopeOverride: false` alone.
**Nothing here creates shared infrastructure.** Private DNS zones, the Log Analytics
workspace and the resource group are referenced, never created. Two deployments each
creating `privatelink.blob.core.windows.net` is a conflict that only surfaces at apply
time, which is why a pattern skill or the platform owns them.

## Naming

Storage account names are the awkward case in the whole CAF convention: globally unique,
3–24 characters, lowercase alphanumeric only. No hyphens — which is why a rendered account
name has none while a vnet's does. The Terraform provider handles that; in Bicep the
template assembles the name from vars and the length is the author's to check.

| Target | What the question set declares |
|---|---|
| Terraform | `naming.terraform` — `Azure::Microsoft.Storage/storageAccounts` |
| Bicep | `naming.abbreviation` — `st`, rendered into a var (see [naming.md](../../core/iac-rendering/references/naming.md)) |

Use those rather than constructing either yourself. The Bicep naming modules
(`utility/naming`, `genName`) are not ready to ship — never import them.

## Adding a resource to this family

1. Create `<resource>/` and write `<resource>/questions.yaml` — see
   [question-set-format](../../core/iac-authoring/references/question-set-format.md)
2. Write `<resource>/notes.md` for what the question set cannot express:
   decisions fixed at creation, dependency order, the pitfalls worth naming
3. Write `<resource>/terraform.md` and `<resource>/bicep.md`
4. Add a row to the routing table above
5. If the resource brings a term people would actually type that the
   [azure-resources](../../core/azure-resources/SKILL.md) description does not already
   carry, add it there — that description is the only trigger this family has

Do **not** add a skill for it. The skill listing has a shared character budget and every
extra entry spends it; azure-resources is the triggering unit, the family the routing unit, the
question set the knowledge unit.
