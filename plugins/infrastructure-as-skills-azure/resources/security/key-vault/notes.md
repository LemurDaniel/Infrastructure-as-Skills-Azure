# Key Vault - what the question set cannot express

## Fixed at creation

- **The name.** Global, 3-24 characters, letters, digits and hyphens. A name from the
  convention can still collide, and 24 characters is tight for a long workload name.
- **Soft-delete retention.** Set when the vault is created and not editable afterwards.
- **Purge protection.** One-way: once on, never off. It also reserves the name for the whole
  retention period after deletion, so a tear-down and re-create under the same name fails
  until it ends.
- **The region and the tenant.**

## Ordering

Identity, vault, the vault's role assignments, then the keys and secret placeholders (a
data-plane write needs the role first - the AVM Terraform module waits for RBAC before key and
secret operations), then the consumers. A consumer's role on a key is granted in the pattern
that wires them, before the consumer exists. The workspace before the diagnostic setting.

## Roles

A role on the vault is a `wiring.role_assignments` entry with it as `to`. With RBAC
authorization nothing can read or write the vault until one exists - not even the identity
that created it - so a vault without a role for its reader works and is of no use to anyone.
A consumer nobody has named is an `open:` entry (key `wiring.role_assignments`) owned by the
workload owner, blocking apply.

Scope to the secret or the key where the consumer allows it - a `key-vault-secret` or
`key-vault-key` resource as `to` - never to the subscription. The roles are the narrow ones:
`Key Vault Secrets User`, `Key Vault Crypto Service Encryption User`, `Key Vault Secrets
Officer` for a writer. `Key Vault Administrator` is a departure that names a person.

## Pitfalls

**A closed vault cannot be filled by a pipeline outside the network.** With
`public_network_access: disabled` the data plane (keys, secrets) is reachable only through the
private endpoint; the control plane (the vault itself) is not affected. A runner outside the
network creates the vault and then fails on the first key or placeholder. Either the runner is
inside, or the vault is created open and closed in a second step.

**Module defaults are not the guardrails.** Both modules default the SKU to `premium`; the
Bicep module defaults `enableVaultForDeployment` to true; the Terraform module defaults public
access to true. Every decision is written on the call.

**RBAC has propagation delay.** A role assignment takes a minute or more to be effective; a
key or secret written right after fails with 403. The Terraform module has
`wait_for_rbac_before_*` inputs for it.

**A placeholder is not safe by itself.** See `secret_placeholders`: neither module protects
a filled-in value from the next deployment.

**Soft delete is not purge protection.** Soft delete is always on and keeps deleted items;
purge protection forbids purging them. A vault with soft delete and no purge protection can be
wiped for good by anyone with the right.

**Trusted-service bypass is not a private endpoint.** `AzureServices` lets a fixed list of
Microsoft services past the firewall; it does not make the vault reachable from anywhere else.

**Throttling.** A vault answers a fixed request rate per region and subscription. An
application that reads a secret per request, not once at start, hits it first.

**Log category names are the platform's.** `AuditEvent` and `AzurePolicyEvaluationDetails` are
checked against `az monitor diagnostic-settings categories list --resource <vault id>` before a
render.

## Not covered here, and why

Certificates and their issuers, Managed HSM, backup of keys and secrets, secret expiry and
rotation of secret values, and Event Grid subscriptions each carry decisions of their own and
have no question set yet; a request for one is said out loud, not improvised.
