# Key Vault secret - what the question set cannot express

## This set or the vault's `secret_placeholders`

The vault's `secret_placeholders` creates **bare slots**: a name, the dummy value, the label
`placeholder`, no expiry, no role. This set is for a secret with a decision of its own. The rule:

| The secret... | Is written by |
|---|---|
| Needs only to exist so a `@Microsoft.KeyVault(...)` reference resolves | `key-vault` - its name in `secret_placeholders` |
| Has a content type, an expiry, a role of its own on the secret, or a value the deployment hands over | This set - and its name is **not** in `secret_placeholders` |

A name in both lists is two writers of one secret: the render refuses it, and an apply that got
past would fail on the second write or, worse, replace the first writer's value. Both renders
use the same guard against overwriting a filled-in value (`ignore_changes` in Terraform,
`@onlyIfNotExists()` in Bicep), so a secret moved from one set to the other keeps its value.

## Fixed at creation

- **The name.** Letters, digits and hyphens, 1-127 characters; a secret is not renamed. The
  consumer's reference names it, so it is chosen for the consumer.
- **Nothing else.** A secret's value, content type and attributes are properties of a *version*.
  Writing a value creates a new version; the previous ones stay, readable by the roles that can
  read versions, until they are deleted or expire.

## Ordering

The vault, the writer's role on it (a data-plane write needs it; see `key-vault/notes.md`), the
secret, then the roles on the secret, then the consumer that references it. A reference to a
secret that does not exist yet fails at the consumer's start: the placeholder exists for that.

## Pitfalls

**A placeholder written without the guard is a destroyed secret.** The AVM modules for a secret
(`modules/secret` in Terraform, `vault/secret` in Bicep) both write the value they are given on
every deployment as a new version; neither guards a filled-in value. A placeholder is therefore
rendered outside the module in both targets, as for the vault's slots. `secure_input` uses the
module, because writing the given value is what it is for.

**A secure input does not stay out of the state by default.** Terraform's `value` attribute is
stored in state (sensitive, but stored). The write-only `value_wo` with `value_wo_version` is not
stored in state or the plan; it needs Terraform 1.11 and an **ephemeral** input variable. Bicep's
`@secure()` parameter is not recorded in the deployment's history, but the pipeline that passes it
holds it - the value comes from the pipeline's secret store, never from a file in the repository.

**The expiry dates the first version only.** Whoever fills in a placeholder writes a new version
with its own attributes, which can have no expiry at all: the `expiry_days` decision is a reminder
the process must carry on, not an enforcement. The Azure Policy that denies a secret without an
expiry date applies to every version a person writes as well.

**An expired secret is still in the vault.** It is simply refused by `@Microsoft.KeyVault(...)`
references, which then show an error in the app's configuration status; nothing deletes it.

**Reference by the versionless URI.** An app setting that names a version stays on it after the
value is replaced. The consumer's reference is the secret URI without the version.

**A closed vault cannot be written by a pipeline outside the network.** The data plane is reachable
only through the private endpoint; see `key-vault/notes.md`.

## Not covered here, and why

Rotation of a secret's value (an Event Grid near-expiry subscription, a Functions rotation
workflow), certificates, and the vault's backup of secrets each carry decisions of their own and
have no question set yet; a request for one is said out loud, not improvised.
