# Azure Files share - what the question set cannot express

## Fixed at creation

- **The protocol.** SMB or NFS; a share is one or the other for life.
- **The name.** 3-63 characters, lowercase letters, digits and single hyphens, unique within the
  account.
- **Premium or Standard.** Set by the account's kind (`FileStorage` or general-purpose v2); a
  share cannot move between them.

## Ordering

The account first (with large file shares and identity-based authentication where needed), then
the share, then its role assignments, then the machines or apps that mount it.

## Pitfalls

**With shared keys off, a share cannot be mounted the usual way.** The account-key mount command
and a connection string both rely on the key. An SMB share then needs identity-based
authentication on the account (Microsoft Entra Kerberos, or AD DS) configured by the account's
owner, and the mounting principal needs an SMB data role. Container Apps and App Service file
mounts take the account key by design; with `local_auth: disabled` they cannot mount the share,
and that is a named departure on this account, not a reason to leave keys on everywhere.

**NFS means no identity, no public endpoint.** An NFS share has no authentication beyond the
network: the account must be closed to the internet, reached through a private endpoint or a
service endpoint, and secure transfer off. The decision `protocol: NFS` forces the account's
posture, recorded as forced.

**Premium is billed for the provisioned size.** A 1 TB Premium share costs 1 TB whether it
holds 1 GB or 1 TB. The quota is the plan, not a cap.

**Role scope on a share is not the Resource Manager id.** The File service's data roles are
scoped to a path of their own; the Terraform provider exposes it as `rbac_scope_id`, Bicep
takes the share's resource id in `roleAssignments` of the module.

**Backup is not soft delete.** Share soft delete (an account property) recovers a deleted
*share*; recovering a deleted *file* is a share snapshot or a Recovery Services vault backup
(`recovery-services-vault`).

## Not covered here, and why

Share snapshots and their schedule, provisioned bandwidth and IOPS on Files Provisioned v2,
Azure File Sync, stored access policies, directory and file ACLs, and SMB multichannel each
carry decisions of their own and have no question set; a request for one is said out loud, not
improvised.
