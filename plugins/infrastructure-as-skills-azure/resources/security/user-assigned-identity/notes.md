# User-assigned identity - what the question set cannot express

## Fixed at creation

- **The name and the resource group.** Neither can be changed; a move is a recreate, and a
  recreated identity gets a **new principal id**, so every role assignment held by the old one
  is orphaned and must be granted again.
- **The region.**

## Ordering

The identity first, then its roles on the resources it will call, then the consumers that
take it. This is the whole reason to use one: the roles exist before the consumer starts - a
Key Vault reference in app settings, a customer-managed key on a storage account.

## Roles

An identity is on both sides of a role, and both are `wiring.role_assignments` entries. With
the identity as `from` it is a role the identity holds on a resource it calls. With the
identity as `to` it is a role granted *on the identity itself*: `Managed Identity Operator`
is the one that lets a principal assign it to a resource it creates, which a pipeline
deploying the consumer needs. Where the deploying principal owns the resource group, the
spec has no entry with the identity as `to`.

## Pitfalls

**Role assignments are propagated slowly.** A role granted to a new identity can take minutes
to be effective; a consumer that starts at once fails with 403 on its first call. A pattern
orders for it and does not retry blindly.

**Deleting an identity does not remove its role assignments.** They remain as unknown
principals, counted against the subscription's limit. A teardown removes the assignments
first.

**A shared identity is a shared blast radius.** Everything the identity may do, every consumer
that holds it may do. Share only where the consumers have the same trust level, and never
across stages.

**A federated subject is exact.** A typo in the subject fails at sign-in, not at apply, with
an error from the issuer's side. Branch, environment and tag subjects are different strings.

**Federated credentials are created one after another.** Concurrent writes to one identity
fail; the Terraform module serialises them, a hand-written loop needs `depends_on` or a
sequential chain.

**System-assigned is the default, not this.** If the consumer is created with the identity
and dies with it, a system-assigned identity is simpler. See `purpose`.

## Not covered here, and why

Entra app registrations and service principals (`azuread`/Graph, not ARM), Entra groups,
managed identities on Kubernetes workloads, and credentials on identities have no question set
and are said out loud, not improvised.
