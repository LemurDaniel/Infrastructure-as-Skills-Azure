# Blob container - what the question set cannot express

## Fixed at creation

- **The name.** 3-63 characters, lowercase letters, digits and single hyphens, unique within the
  account. Renaming is a copy and a delete.
- **Immutability with versioning**, in one direction: once a container holds blobs under a
  locked retention, the container cannot be deleted until they expire.
- **The account**, which is the parent: a container cannot move.

## Ordering

The account first, then the container, then its role assignments, then the consumers. With the
account module the container is part of the account's call and the order is internal; the
roles on the container need the principal, which the identity set creates before.

## Pitfalls

**Anonymous access is two switches.** The container's `public_access` and the account's
`allow_blob_public_access` must both allow it; the account set turns the second off, so a
container asking for `Blob` on such an account is refused at apply. The default `None` never
trips it.

**Immutable storage with versioning excludes point-in-time restore.** The account cannot have
both. The decision `immutable_storage: true` forces versioning on and restore off on the
account, recorded as forced; a deployment that needs both for different data uses two accounts.

**A role on the container is narrower than a role on the account.** Prefer it: a worker that
writes to `uploads` has no business reading `exports`. The account-level data roles belong to
the account set and are for the deploying principal.

**With shared keys off the data plane is Entra-only.** A tool or a library that connects with
the account key or a connection string cannot read or write the container; it needs a data
role and a token. A SAS signed with the account key stops working; a user-delegation SAS still
does.

**A closed account is closed to the container too.** Data-plane access to the blobs follows
the account's network rules and private endpoints; the container cannot open what the
account closed. Creating the container through Resource Manager needs no network path.

## Not covered here, and why

Lifecycle management (tiering and deletion by age), blob index tags, object replication,
encryption scopes themselves, stored access policies, SFTP local users and Data Lake Gen2
file systems and their ACLs each carry decisions of their own and have no question set; a
request for one is said out loud, not improvised.
