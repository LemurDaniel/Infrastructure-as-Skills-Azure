# Availability Set - what the question set cannot express

## Why the proximity placement group is in this set

A proximity placement group has a name, a location, an optional zone and a list of sizes. It
carries no decision of its own that is not about the things placed in it, it is created
alongside the availability set it is most often used with, and both AVM modules take its id
as one parameter of the set. A separate `proximity-placement-group` set would be four files
for five questions and a second routing row for a request that always says "availability set"
or "VM" in the same breath. It is therefore a group of questions here (`proximity`), off
unless the customer says that latency matters more than spread. If a PPG without a set ever
carries real decisions of its own (colocation status, Ultra disks, a capacity story), it
becomes its own set and this one keeps the reference.

## Fixed at creation

- **The fault and update domain counts**, and the `Aligned` / `Classic` kind.
- **The membership.** A machine is put into a set when it is created and cannot be moved in
  or out without being recreated.
- **The name and the region.** A set and its machines are in one region.
- **The proximity group's zone**, if it has one.

## Ordering

The proximity placement group (if any), then the availability set that references it, then the
machines that reference the set. The set is removed last: it cannot be deleted while a machine
is in it, and a machine cannot be removed from it while it exists.

## Pitfalls

**A set and a zone exclude each other.** A machine in a set has no zone; a machine in a zone
has no set. The set is for a region without availability zones or a workload that cannot be
zonal. Where zones exist, two zonal machines behind a load balancer survive the loss of a
datacenter, which a set does not.

**A set is not a load balancer.** It guarantees that machines are not on the same rack and not
rebooted together; it does not route traffic. Two machines in a set with nothing in front of
them are two machines.

**Fault domains cannot exceed the region.** Two or three, depending on the region; a count
above it fails the deployment. The azurerm resource's documented default is 3, the Bicep
module's 2: both are written.

**A proximity group trades availability for latency.** All machines in it are in one
datacenter; a datacenter incident takes them together. A group that serves an availability
set carries no zone, because a zonal group accepts only zonal machines.

**Capacity decides, not the template.** The first machine in a proximity group fixes the
datacenter, and a later machine of another size or family may find no room there. The sizes
listed on the group (`allowed_vm_sizes`, `intent`) are the mitigation. Starting a deallocated
machine can fail the same way; the remedy is to deallocate all and start together.

**The AVM Terraform proximity module pins `azurerm` below 5.0.** A root on 5.x uses the
authored resource for the group; the authored availability set already is one (no AVM
Terraform module exists for it).

## Not covered here, and why

Capacity reservation groups, dedicated hosts and host groups, and the placement of machines in
a scale set (Flexible scale sets spread their own instances over fault domains) each carry
decisions of their own and have no question set; a request for one is said out loud, not
improvised.
