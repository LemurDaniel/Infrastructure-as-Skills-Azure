# Backup vault - what the question set cannot express

## Fixed at creation

- **Storage redundancy.** `LocallyRedundant`, `ZoneRedundant` and `GeoRedundant` cannot be
  changed on a vault; a different choice is a new vault and re-protecting every item.
- **The datastore type** of the vault's storage.
- **Double encryption** (`infrastructureEncryption`).
- **`Locked` immutability.** One-way: a locked vault keeps every backup to its expiry, for
  everyone, and cannot be unlocked or deleted until the last one expires.
- **The name** (5-50 characters) and the region. A vault protects resources of its own region.

## Ordering

Resource group (its own, for `isolated` and `immutable`), identity and key (customer-managed key
only), the vault, **the vault's role on each protected resource**, the backup policy, the backup
instance, then the alerts. The Resource Guard exists before the vault is associated with it, in
another subscription. The workspace before the diagnostic setting. A backup instance created
before the role is effective fails in `ConfiguringProtection`; the module's wait covers the
service delay, not a missing role.

## Pitfalls

**A separate vault is not a separate authority.** `isolated` means the copies live outside the
workload's resource group - but an administrator of the subscription can still delete the vault.
What makes the copies survive them is the combination: a vault in its own group or subscription
with its own access, soft delete `AlwaysOn`, and a Resource Guard that a second team holds. The
interview's answer is the *requirement*; the decisions here are how it is met, and the handover
says which part (the guard, the subscription) is somebody else's.

**Locked immutability and a long retention are paid for to the last day.** With `Locked`, a
policy with a retention of 120 days produces 120 days of storage for every recovery point, and
nothing can shorten it. Test with `Unlocked` first; lock in production once the policy is right.

**Soft delete is not retention.** `retention_days` is how long a recovery point lives;
`soft_delete_retention_days` is how long a *deleted* one can still be rescued. Both cost storage,
and only the first answers "how far back can I restore".

**The vault's identity needs a role on every protected resource.** `Storage Account Backup
Contributor` for blob backup, `Disk Backup Reader` and `Disk Snapshot Contributor` for disks. The
roles are wiring and belong to the pattern; a vault without them fails to protect and the error
appears on the instance, not the vault.

**Blob backup keeps changing underneath.** Vaulted blob backup takes a copy per schedule, but
point-in-time restore and versioning on the storage account are separate and cheaper features.
`data_loss_tolerance` derives both; the vault is the answer to `isolated` and `immutable`, not
to a mistaken overwrite an hour ago.

**The Resource Guard cannot be created here.** It must sit in a different subscription (ideally
a different tenant, through Lighthouse) owned by a security team. When nobody supplied one, the
`open:` entry blocks the apply for `isolated` and `immutable`, rather than a guard being created
in the same subscription, where it protects nothing.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <vault id>` before a render.

## Not covered here, and why

Cross-subscription restore, archive tier policies, vault-to-vault replication and the
Azure Backup Center views each carry decisions of their own and have no question set; a request
for one is said out loud, not improvised. Virtual machines, Azure Files and SQL in a VM use the
Recovery Services vault.
