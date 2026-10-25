# Recovery Services vault - what the question set cannot express

## Fixed at creation

- **Storage redundancy** can be changed only while nothing is protected. After the first item it
  is fixed; a different choice is a new vault and re-protecting everything.
- **`Locked` immutability** and **`AlwaysOn` soft delete** are one-way.
- **The name** (2-50 characters) and the region. A vault protects resources of its own region.

## Ordering

Resource group (its own, for `isolated` and `immutable`), identity and key (customer-managed key
only), the vault, **the vault's role on the protected resource** where one is needed (a file
share's storage account), the backup policy, the protected item, then the alerts. The Resource
Guard exists before the vault is associated, in another subscription. The workspace before the
diagnostic setting.

## Pitfalls

**Which vault.** The Recovery Services vault protects virtual machines, Azure Files shares and
SQL or SAP HANA in a VM, and replicates machines for Site Recovery. Blobs, data lake storage,
disks, PostgreSQL flexible server and AKS go to the Backup vault. A request for "backup" of a
storage account asks which: file shares here, blobs there.

**The modules disagree on defaults.** Public access is on in Terraform and off in Bicep;
cross-region restore is on in Terraform and unset in Bicep; both default to geo-redundant
storage. Every decision is written on the call.

**A customer-managed key and a private vault do not mix with a user-assigned identity.** A
vault whose key is read through a user-assigned identity cannot use private endpoints for
backup. A private vault with a customer-managed key uses the system-assigned identity, which
exists only after the vault: the key role is granted in a second step and the encryption set
afterwards.

**A private vault needs more than its own endpoint.** The backup service reaches the protected
resources and their storage over the private path: the DNS zones for the backup service
(`privatelink.<region>.backup.windowsazure.com`, blob, queue) and the network rules of the
storage that holds the data must all resolve and allow it. A missing zone shows up as a backup
job that fails with a connectivity error, hours after the apply.

**`Locked` immutability and a long retention are paid for to the last day.** Test with
`Unlocked` first; lock in production once the policy is right.

**Soft delete is not retention.** `retention_days` is how long a recovery point lives;
`soft_delete_retention_days` is how long a *deleted* one can still be rescued. The Terraform
module has no input for the second and the platform default applies.

**Enhanced policies cannot be undone.** A VM policy of type `V2` (several backups a day,
longer retention) cannot be converted back to `V1`, and not every VM size supports it.

**The Resource Guard cannot be created here.** It sits in a different subscription (ideally a
different tenant) owned by a security team. When nobody supplied one, the `open:` entry blocks
the apply for `isolated` and `immutable`.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <vault id>` before a render.

## Not covered here, and why

Site Recovery (replication fabrics and policies, replicated machines), MARS-agent backup of
on-premises servers, SQL and SAP HANA in-VM workload backup policies, archive-tier policies and
cross-subscription restore each carry decisions of their own and have no question set; a request
for one is said out loud, not improvised.
