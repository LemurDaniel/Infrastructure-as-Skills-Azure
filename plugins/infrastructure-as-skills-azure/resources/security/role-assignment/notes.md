# Role assignment - what the question set cannot express

## Wiring or this set

**A role between two resources of the spec is wiring; an assignment at a scope that is no
resource of the spec is a resource of this set.** The first is a relationship the spec can
name on both ends (`wiring.role_assignments`, `{ from, to, role }`), and how it renders is
[role-assignments.md](../../../core/iac-rendering/references/role-assignments.md).
The second has no `to` the wiring could name, so it is a resource with decisions of its own:
the scope, the principal, the role, a condition.

| The assignment is... | Recorded as |
|---|---|
| Between two resources of the spec - the app on the vault, an identity on the storage account - or from a principal outside the spec (a group of people, a pipeline) onto a resource of the spec | A `wiring.role_assignments` entry. No resource of this set |
| On a narrower resource of the spec - one secret, one key, one container that has a resource key of its own | A `wiring.role_assignments` entry with that resource as `to` |
| At **resource group, subscription or management group** scope | A resource of this set. No resource of the spec is the scope |
| On a resource the spec does not create (a referenced platform workspace, a hub) | A resource of this set, and the principal's right to write there is an `open:` entry owned by the platform team |
| On a resource of the spec, with a **condition** | A resource of this set (`scope_kind: resource`): a wiring entry is `{ from, to, role }` and carries no condition |

The two never record the same assignment: a role in `wiring.role_assignments` is not repeated
as a resource of this set. The check that finds a duplicate is the plan - two writers of one
assignment fail at apply with `RoleAssignmentExists`.

## What the deploying identity needs

Not in the spec by derivation (`pipeline_auth` says how the pipeline signs in, not what it may
do), so `deployer_role` records it. For every scope the spec writes an assignment on, the
deploying identity needs, **at that scope or above**:

- **`Role Based Access Control Administrator`** with a condition listing the role definition
  ids the spec assigns - the least privilege - or without one (any role below the scope); or
  `User Access Administrator`, or `Owner`.
- **Not `Contributor`.** It excludes `Microsoft.Authorization/*/Write`; the plan succeeds and
  the apply fails with `AuthorizationFailed` on the first assignment.
- For a subscription or management group scope the right is held there, and it is the
  platform's to grant.

A non-empty `key-vault.secret_placeholders` or any key and secret written by the pipeline
needs a data-plane role on the vault (`Key Vault Secrets Officer`, `Key Vault Crypto Officer`)
- granted by an assignment of this set, with the pipeline as the principal, before the first
key or secret. The handover lists both rights with the scope each is needed at.

## Fixed at creation

- **The name (a GUID), the scope, the principal and the role.** None of the four can be
  edited: a change is a delete and a create, and the access has a gap in between. The render
  derives the name from `scope`, `principal` and `role`, so the same spec always names the same
  assignment; an assignment someone created by hand with a random GUID is not adopted and
  fails as `RoleAssignmentExists` for the same triple.

## Ordering

The scope's resource, the principal, then the assignment, then whatever relies on the access.
The assignment is the last thing before the consumer starts - the cycle the other order makes
is the usual first failure (see the family's routing notes).

## Pitfalls

**Propagation takes minutes.** A new assignment is not effective at once; the first call by the
principal fails with 403. Ordering and a wait handle it (the Key Vault Terraform module has
`wait_for_rbac_before_*` inputs, an assignment of this set uses `time_sleep` after it when a
data-plane write follows). Do not retry in a loop.

**A principal created seconds earlier is not in the directory yet.** `principal_type` is always
written, which skips the lookup; `skip_service_principal_aad_check` is the older switch for the
same failure and is not needed with a type.

**Deleting the principal does not delete the assignment.** The assignment stays behind as an
"identity not found" entry and counts against the subscription's limit (4000). A teardown
removes the assignments first, or the principal's module does.

**The limit.** 4000 assignments per subscription, 500 per management group. A group as the
principal is the answer when the number of principals grows, not another assignment.

**The same role twice.** Two entries with the same scope, principal and role are one
assignment; the second fails. Descriptions and conditions are not part of the identity.

**A condition is not portable.** It is valid only for roles and resource types that support
attribute-based conditions (storage blobs, and `Role Based Access Control Administrator`
among them), and a syntax error is reported by the API at apply, not by `validate`.

**Principal type and managed identity.** There is no `ManagedIdentity` value in the ARM API;
`ServicePrincipal` is the right value for a user-assigned or system-assigned identity. The
`UserAssignedManagedIdentity` / `SystemAssignedManagedIdentity` types of the Terraform module's
principal helpers are the module's own and are not passed to Azure.

## Not covered here, and why

Custom role definitions, PIM eligible assignments, deny assignments, Entra directory roles and
cross-tenant delegation each carry decisions of their own and have no question set; a request
for one is said out loud, not improvised.
