# Container Instances - what the question set cannot express

## Fixed at creation

- **The subnet and the address type.** A group is created public or into one delegated subnet and
  is not moved; changing either replaces it.
- **The zone, the OS type and the SKU.** All set when the group is created.
- **The container definition.** A group is immutable apart from a few properties: a new image, a
  new size, a new environment variable or a new port is a **replacement** of the group, which
  loses its state and, on a public group, its address.
- **The customer-managed key's version.** Pinned at deployment; ACI does not follow a rotation.
- **The name**, which forms the address of a group with a DNS name label.

## Ordering

The identity and its role on the registry (`AcrPull`) and on the key, the network and the
delegated subnet, then the group. The group pulls its image during creation, so the role must
already be effective: a role granted at the same apply is usually not yet, and the failure looks
like a bad image. The workspace before the group, because the logging configuration is part of its
creation.

## Pitfalls

**A public group has no network controls.** No firewall, no network security group, no private
endpoint: every exposed port is open to the whole internet. A container that must be reachable
only from the company network is injected into a subnet (`ip_address_type: private`), not
protected some other way. `public` is the "public, unrestricted" rung of the posture ladder and
is a recorded departure.

**A subnet-injected group is limited.** The subnet is delegated to
`Microsoft.ContainerInstance/containerGroups` and holds nothing else; the group reaches the
internet only through the network's routes, so a subnet whose default route goes to the platform's
firewall needs rules for the registry and the workspace. A registry with a private endpoint needs
its DNS reachable from the subnet.

**A restarting group is billed forever.** `Always` restarts a container that finished its job;
the group never ends. `OnFailure` and `Never` end when the work does. The group stopped costs
nothing, deleted or not.

**An image never updates by itself.** A tag that moves does not change a running group; it is
pulled once, at start. A new version is a new deployment or a restart of the group.

**The shared key for logs.** The only way to get a container's console output into a workspace is
the workspace's id and shared key. The Bicep module reads the key during deployment; the
Terraform module takes it as an input, so it is in state - treat the state accordingly and keep
the key out of outputs. Azure Monitor metrics are a separate path that neither module wires.

**Secrets are the container's job.** An environment variable of a group is stored with the
definition (the secure ones are masked when read back) and there is no Key Vault reference. The container reads the vault itself with its identity at
start, or a secret is injected by a pipeline step that does not write it into the template.

**The Terraform module takes only a user-assigned identity for the registry sign-in**, and has
inputs for private endpoints that the service does not support; a private endpoint is not a
way to close a container group.

**The modules disagree on defaults.** Restart policy (Bicep `Always`, Terraform required), the
IP address type (Bicep sends `Public` when an `ipAddress` is given without a type, Terraform
derives `Private` from a non-empty subnet list), the
log type (not exposed in Terraform). The Bicep module requires an `availabilityZone`. In the
Bicep module's version at the time of writing the DNS name label scope is sent only together
with custom DNS servers, which is why no label is rendered.

**No role assignments in the Bicep module.** The assignment is written beside the module, scoped
to the group, as in the call.

## Not covered here, and why

Volumes (a file share needs the storage account key), several containers and sidecars, init
containers, probes, GPU, Windows containers, spot priority, confidential and dedicated SKUs,
container group profiles and standby pools, custom DNS servers and name labels, and metrics
export each carry decisions of their own and have no question set; a request for one is said out
loud, not improvised. A workload that needs scaling, revisions, ingress with TLS or secrets from
a vault belongs on Container Apps.
