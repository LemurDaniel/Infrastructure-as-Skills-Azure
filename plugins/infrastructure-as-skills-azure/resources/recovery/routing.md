# Azure recovery resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| Backup vault, vaulted blob backup, backup of a storage account, blob backup, disk backup, PostgreSQL backup, AKS backup, ransomware protection for storage, immutable backup | `backup-vault/questions.yaml` | [notes](backup-vault/notes.md) |
| Recovery Services vault, VM backup, Azure Files backup, file share backup, SQL in a VM backup, Azure Backup | `recovery-services-vault/questions.yaml` | [notes](recovery-services-vault/notes.md) |
| Site Recovery, disaster recovery of VMs, replication, failover to a second region | *not yet written* | The Recovery Services vault set does not configure Site Recovery |
| Resource Guard, multi-user authorization | see `multi_user_authorization` in either set | The guard itself lives in the security team's subscription and is an `open:` entry |
| Cosmos DB backup, continuous backup, point-in-time restore | see the [data](../data/routing.md) family | Not here - the account carries its own backup |
| Storage soft delete, versioning, point-in-time restore | see the [storage](../storage/routing.md) family | Not here - protection inside the account |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers `backup_isolation`, `data_loss_tolerance`, `outage_impact` and `data_residency`
   before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**These sets are where `backup_isolation` is rendered.** `operational` needs no vault: the
protection is inside the resource (soft delete, versioning, point-in-time restore) and the
resource's own set renders it. `isolated` and `immutable` are the two answers that need a
vault of their own, and a deployment that answers either is missing a protected resource
without one. The pattern that adds a vault adds a `protected_resources` entry for each
resource that needs it, and the vault's identity is granted its role on each.

**Backup is the one thing that must outlive the thing it protects.** The vault belongs in a
resource group, and where possible a subscription, that the workload's administrators cannot
delete: the `security` group of a split (`deployment.resource_group_layout: split`) is the minimum, a
subscription of its own the better answer. Redundancy and residency are decided per vault and
fixed once items are protected.

**A backup that was never restored is a hope.** The sets render the vault, the policy and the
alert; the restore test is the customer's and belongs in the handover.
