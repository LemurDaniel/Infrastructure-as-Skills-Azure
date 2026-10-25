# Managed Disk - what the question set cannot express

## Fixed at creation

- **The zone.** A disk in zone 1 stays there; moving it is a snapshot and a new disk.
- **The create option and the source.** A copy is made once; changing the source forces a
  new disk.
- **The redundancy family.** LRS to ZRS (and back) is a copy, not a setting.
- **The name.**
- **The region**, and with it the disk types and the zones that exist.

## Ordering

The disk encryption set and its key (for `customer_managed`), the disk access resource (for
`allow_private`), then the disk, then the private endpoint, then the role assignments, then
the attachment to the machine - which is the machine's, and needs the disk's id and the
machine's zone to match the disk's.

## Pitfalls

**A disk's zone must match the machine's.** A zonal LRS disk can be attached only to a machine
in the same zone, and the error comes at attach time, not at plan. A ZRS disk has no zone and
attaches to a machine in any of them, which is why it is the derived default for a
`disruptive` outage.

**The size is the tier.** A disk of 129 GiB is billed as the 256 GiB tier. The next tier is the
cost, not the byte.

**The modules disagree on network defaults.** Terraform: `AllowPrivate` with public access off.
Bicep: `DenyAll` with public access `Disabled`. Both are written. The Bicep module has no input
for a disk access resource or a private endpoint, so `allow_private` is rendered in Bicep only
as the authored resource.

**A detached disk keeps billing.** Deleting the machine leaves a data disk behind unless the
machine's `deleteOption` is `Delete`. The disk is the one thing in a machine's resource group
that holds data and costs money with nobody using it.

**Backup is not on this resource.** Neither module has a backup input. A disk attached to a
machine is protected with the machine in the Recovery Services vault (the machine's
`backup_enabled`), and the machine's `exclude_disk_luns` / `include_disk_luns` choose which
disks. A disk without a machine is protected in the Backup vault as a protected resource of
its own.

**Encryption at the host and a disk encryption set are not the same thing.** The set wraps the
disk's key with the customer's key; encryption at the host is the machine's switch and covers
the temporary disk and the cache. A customer-managed key needs both for the data not to reach
the host unencrypted.

**Deleting the key makes the disk unreadable.** That is the capability a customer-managed key
buys, and it applies to snapshots of the disk made with the same set.

## Not covered here, and why

Ultra disks and Premium SSD v2 (zone, IOPS, throughput and sector size, and no encryption at
host on some), shared disks, on-demand bursting and performance plus, performance tier changes,
snapshots and restore points, images and galleries, disk pools and elastic SAN, trusted-launch
and confidential disk security types for OS disks, and uploading a VHD each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
