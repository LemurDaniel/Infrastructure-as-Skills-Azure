# AKS - what the question set cannot express

## Fixed at creation

- **The network model**: plugin mode (overlay or VNet), dataplane, network policy engine, pod
  and service ranges, the DNS service address and the outbound type. Changing one is a new
  cluster, or an in-place migration with downtime that this set does not render.
- **A private cluster.** The API server is private from the first minute; a public cluster is
  not made private by editing the template, and the DNS zone mode (`system` or custom) goes
  with it.
- **The zones of a node pool, its VM size and its subnet.** A pool is replaced, not edited; the
  system pool is the default pool and cannot be renamed or removed, so its replacement is a
  cluster rebuild unless a second system pool is added first.
- **Encryption at host and the disk encryption set** on a pool.
- **The cluster name and region**, and with them the API's DNS name.
- **Kubernetes versions only move forward.** A minor version cannot be downgraded, and an
  unsupported one stops receiving fixes; the auto-upgrade channel decides who moves it.

## Ordering

The identity and its roles (`Network Contributor` on the node subnet, `Private DNS Zone
Contributor` on a custom zone), the network and the subnet, the disk encryption set, the
cluster, then the roles that need the cluster's own identities: `AcrPull` for the **kubelet
identity** on each registry, and the role assignments for people. The workloads' federated
credentials come after the cluster, because they need its OIDC issuer URL. The workspace before
the cluster's diagnostic setting and the monitoring add-on.

A role granted in the same apply as the cluster is usually not yet effective: the first image
pull or load balancer creation fails on propagation, and the failure looks like a broken cluster.
Grant first, then create.

## Pitfalls

**Private means the pipeline sits inside the network.** `kubectl`, Helm and the GitOps agent
reach a private API server only from the VNet or a peered network. A deployment runner outside
it fails at the first call, not at plan time. `az aks command invoke` goes through the control
plane and is the escape hatch; a self-hosted runner in the network is the answer. This is a
decision for the pipeline, not for this set.

**The pod range is not the service range is not the VNet.** Three address spaces: the node
subnet (from the platform), the pod CIDR (overlay only, not routed) and the service CIDR (never
routed). The AKS default service range `10.0.0.0/16` overlaps most hub networks, which sends a
pod's traffic to its own service instead; the set defaults to `172.20.0.0/16`. The pod and service
ranges must not overlap each other, the VNet, a peering or an on-premises range.

**`userDefinedRouting` needs the firewall to be ready.** The route table must send egress to the
firewall and the firewall must allow the AKS required endpoints (the control plane's
`AzureKubernetesService` FQDN tag, the registry, the package mirrors) before the first node
joins. Otherwise nodes stay `NotReady` and the cluster fails with a timeout that names no cause.
The platform owns both; this set records only that it expects the route.

**An empty `authorized_ip_ranges` is not a closed API.** On a public cluster it means no
restriction at all. The set refuses to render it: no ranges is an open decision.

**Kubernetes RBAC and Azure RBAC are two systems.** With `azure_rbac_enabled` the Azure roles
(`Azure Kubernetes Service RBAC Reader`, `Writer`, `Admin`, `Cluster Admin`) decide, and a
Kubernetes `RoleBinding` to a user still works beside them - which is the second system nobody
reviews. The admin group bypasses both. Local accounts off means `az aks get-credentials
--admin` stops working; a locked-out cluster is recovered only through the admin group, so the
group is mandatory.

**The cluster identity is not the kubelet identity.** The cluster identity manages Azure
resources (load balancers, disks, routes); the kubelet identity pulls images and is created with
the cluster. `AcrPull` goes to the kubelet identity. Workload identities are a third kind, one
per workload, and are not this cluster's.

**The modules disagree on defaults.** Tier (Bicep `Standard`, Terraform `Free`), upgrade channel
(Bicep `stable`, Terraform `none`), local accounts (Bicep disabled, Terraform allowed), the
OIDC issuer (Bicep off), the Azure Policy add-on and Container insights (Bicep on), the Key
Vault secrets provider (Bicep off), public network access (Bicep `Disabled`). Every decision is
written on the call.

**Auto-upgrade without a window upgrades at any time.** Maintenance configurations (the planned
maintenance window for control-plane and node upgrades) are not rendered; both modules support
them. Until there is a set for it, the handover names the gap, and a production cluster on
`patch` or `NodeImage` has upgrades with no window.

**Container insights and the data collection rule.** With managed identity authentication the
agent needs a data collection rule associated with the cluster. The Terraform module creates it
with `onboard_monitoring`; whether the Bicep module does is read from its README for the version
pinned. A cluster with the add-on enabled and no rule sends nothing.

**Ephemeral OS disks need the right VM size.** `Standard_D4ds_v5` carries a cache and a temp disk
large enough for the default 128 GiB OS disk; a size with no `d` (no local disk) fails at pool
creation. Zones, quota and `EncryptionAtHost` registration are checked against the subscription,
not the template.

**Log category names are the platform's.** Checked against `az monitor diagnostic-settings
categories list --resource <cluster id>` before a render.

## Not covered here, and why

Everything that runs inside the cluster (namespaces, Helm, Flux, ingress, service meshes,
admission policies), managed Prometheus and Grafana, alert rules, AKS backup, maintenance
windows, the cluster autoscaler profile, KMS etcd encryption, API-server VNet integration,
HTTP proxy, Windows, GPU and spot pools, additional user pools, node auto-provisioning (Karpenter)
and AKS Automatic each carry decisions of their own and have no question set; a request for one
is said out loud, not improvised.
