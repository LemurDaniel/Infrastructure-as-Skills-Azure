# Virtual Machine Scale Set - what the question set cannot express

## Fixed at creation

- **The orchestration mode.** Flexible does not become Uniform, and back.
- **The zones and the fault domain count.**
- **Trusted launch and the OS type.**
- **The name** (which seeds the instances' computer names) and the home region.
- **Whether the set is in a proximity placement group.**

## Ordering

The subnet and the disk encryption set (for `customer_managed`), the user-assigned identity and
its roles elsewhere, the load balancer or Application Gateway with its backend pools, then the
scale set, then the roles on the set, then the autoscale setting. The identity's roles need to
have propagated before the first instance starts if the instance reads a secret or a blob as it
boots - the cause of the usual "first instance unhealthy, the next one fine".

## Pitfalls

**Flexible is a different thing from Uniform.** Instances are ordinary virtual machines in
the resource group, visible and individually addressable; there is no instance view of a
model, no overprovisioning and no single placement group. Features written for Uniform
(`overprovision`, `doNotRunExtensionsOnOverprovisionedVMs`, a placement group of 1,000) do not
apply, and a Terraform AVM module renders Flexible only.

**No system-assigned identity.** A Flexible set supports user-assigned identities only (the
Terraform module refuses the other). One consequence is unverified here: the Entra
sign-in extension for Linux needs a system-assigned identity, so signing in to a Flexible
instance with a company account may not be possible; access is by key and the private
network.

**Health check first.** Instance repair, rolling upgrades and platform patching all need a
health signal - the application health extension or a load balancer probe. The Terraform
module refuses `automatic_instance_repair` and `upgrade_mode = "Rolling"` without the
extension. A health path that always answers 200 repairs nothing.

**The autoscale setting and `instances` fight.** The template's `instances` is the capacity
the set starts with. Once an autoscale setting exists it changes the capacity; a later apply
of the template resets it to the template's number unless the capacity is ignored in
lifecycle (Terraform `ignore_changes`) or left unset (Bicep). Where autoscale exists, the
template states a minimum and does not manage the count.

**Instances are made from today's image.** With `latest`, a scale-out in six months builds
from a newer image than the instances that already run. A pinned gallery image makes the
fleet uniform; replacing instances with a new image is the patch.

**The modules disagree on defaults.** Encryption at host (Bicep on, Terraform unset), and the
set of things only one of them can carry: trusted launch and a diagnostic setting are Bicep
only, the Uniform mode is Bicep only (and authored Terraform), the Application Gateway pool
reference is a free-form property in Bicep. Every decision is written on the call, and a
decision the module cannot carry is named in the handover.

**The Terraform module takes two ephemeral inputs.** `extension_protected_setting` and
`user_data_base64` are required, ephemeral variables, `{}` and `null` when unused. It needs
Terraform 1.10 or later for that reason, and a root that wraps it must pass them through.

**Subnet capacity.** Every instance takes an address; a scale-out into an exhausted subnet
fails, and the failure reads as an allocation error. Size the subnet for the maximum.

**Quota and capacity.** A region's vCPU quota per size family is checked at scale-out, not at
deployment of the set; a set of four can be created and fail to grow to forty.

## Not covered here, and why

Autoscale rules, scheduled actions and predictive scaling, Spot priority mixes and eviction,
scale-in policy, ephemeral OS disks, instance protection, termination notification, the
Azure Monitor Agent and Data Collection Rules, Defender for Servers, scheduled events, and
the Uniform-only features (overprovisioning, single placement group) each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised. A
Service Fabric or AKS node pool is not a scale set to configure by hand.
