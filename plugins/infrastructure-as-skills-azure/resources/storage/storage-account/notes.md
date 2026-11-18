# Storage account — what the question set cannot express

Read alongside [questions.yaml](questions.yaml).

## Decisions fixed at creation

Three answers cannot be changed later without replacing the account and migrating the data.
Terraform plans a `-/+` for them, which for a storage account means data loss. Call them out
while interviewing, not while reviewing the plan:

| Decision | Why it is terminal |
|---|---|
| `infrastructure_encryption_enabled` | Settable only at creation |
| `replication` across the local/geo boundary | LRS↔ZRS and GRS↔GZRS convert in place; local↔geo does not |
| hierarchical namespace (implied by `sftp_enabled`, ADLS Gen2) | Not convertible in either direction |

If the user wants ADLS Gen2 semantics, that is hierarchical namespace and has to be decided
now. Ask if the request mentions a data lake, Databricks, Synapse or Fabric.

## Disabling shared keys breaks consumers silently

`local_auth: disabled` is a one-line diff and a dead application, because the
failure is a 403 at runtime rather than anything at apply time.

For a **new** account it is free — there are no consumers yet, which is exactly why the
switch belongs in the initial generation and not in a hardening pass later. For an
**existing** account, say what has to move to managed identity first.

## A locked-down account nobody can read is the default outcome

With shared keys off, access needs a role assignment, and `role_assignments` defaults to
empty. An account generated with no assignment is working as specified and useless.

Flag it: either name the consumer and assign the role, or state explicitly that assignments
come later. And use the **data-plane** roles — `Storage Blob Data Reader`,
`Storage Blob Data Contributor`. `Contributor` is control-plane and grants no data access
whatsoever, which is worth catching in review: an application given `Contributor` on a
storage account still cannot read a blob.

## Dependency order

The account is rarely the first thing created, and the ordering trips up every first
attempt:

1. Resource group, subnet, Log Analytics workspace — all expected to exist already.
2. For customer-managed keys: the Key Vault key **and** the account's identity holding
   wrap/unwrap on it, before the account itself. With a system-assigned identity this is
   circular — the identity does not exist until the account does — so either create the
   account with platform keys and apply the CMK configuration in a second step, or use a
   user-assigned identity. Prefer user-assigned when CMK is in scope; it removes the cycle
   entirely and lets the grant exist beforehand.
3. Private DNS zone before the private endpoint, or the endpoint resolves to nothing. The
   failure presents as a connection timeout rather than a DNS error, which makes it
   needlessly hard to attribute.

## Diagnostics attach to the service, not the account

Blob data-plane logs attach to `<account id>/blobServices/default`. A diagnostic setting on
the account alone collects no `StorageRead`, `StorageWrite` or `StorageDelete` events while
looking fully configured — a silent gap, and the one worth checking in review.
