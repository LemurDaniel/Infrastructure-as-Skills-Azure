# Azure security resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| Key Vault, vault, secrets, keys, certificates, CMK | `key-vault/questions.yaml` | [notes](key-vault/notes.md) |
| managed identity, user-assigned identity, MSI, federated credential | `user-assigned-identity/questions.yaml` | [notes](user-assigned-identity/notes.md) |
| Entra app registration, service principal, enterprise application | *not written - not an Azure resource* | Directory objects (`azuread`, Graph), not ARM. Recorded as an `open:` entry owned by the identity team, never rendered |
| Managed HSM | *not yet written* | `key_protection: hsm` selects Premium here; a single-tenant HSM is its own set |
| role assignment, RBAC, role, grant access, "Rolle zuweisen", Zugriff vergeben, least privilege | `role-assignment/questions.yaml` | [notes](role-assignment/notes.md) - a resource's own `role_assignments` go through its module interface |
| Key Vault key, signing key, CMK key, key rotation, Schlüssel | `key-vault-key/questions.yaml` | [notes](key-vault-key/notes.md) - a key with its own decisions; uniform CMK keys stay in the vault set |
| Key Vault secret, connection string secret, secret expiry, Geheimnis | `key-vault-secret/questions.yaml` | [notes](key-vault-secret/notes.md) - a secret with its own decisions; bare slots stay `secret_placeholders` of the vault |
| Defender for Cloud, Defender plan, Defender for Servers, Defender for Storage, security contact, CSPM | `defender-for-cloud/questions.yaml` | [notes](defender-for-cloud/notes.md) - subscription scope; nothing renders by default (`defender_ownership: platform`) |
| Sentinel, policy | *not yet written* | - |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, `local_auth`, `key_protection` and `key_management` before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**Security resources are what the other families' decisions point at.** `key_management:
customer_managed` on a storage account, a Key Vault reference in an app setting, a role
granted to an identity - each names a vault or an identity that has to exist first. The
sets here are therefore small and almost entirely inherited: a customer is asked nothing
new, and the engineer's own questions are the few that are the resource's.

**Identities and roles come before the things that use them.** A user-assigned identity
exists to hold its roles before the consumer is created: a Key Vault reference in an app's
settings, a customer-managed key on a storage account. The order in a composition is
identity, vault, role assignment, then the consumer - the cycle the other order produces is
the usual first failure.

**No secret value is ever in a template.** The sets create vaults, keys and identities.
A secret is created as a *placeholder* - a dummy entry the consumer's reference can
resolve - and its real value is filled in afterwards, by hand or by the workload. The
placeholder must never overwrite the real value on a later deployment, which no AVM module
guarantees; the Key Vault set says how each target guards it.

**Special case, Bicep: `@onlyIfNotExists()` on a secret.** A secret resource that carries the
decorator is deployed only when it does not exist yet, so the placeholder is written once and a
later deployment never overwrites the value somebody set. It is the default: the toolchain is
assumed to be the latest Bicep, so the render has no lookup of existing secrets, no parameter for
one and no pipeline step (see [key-vault/bicep.md](key-vault/bicep.md)). Terraform has no
equivalent: `ignore_changes = [value]` keeps a changed value, and the placeholder is still
created by the module's own resource.
