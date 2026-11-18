# Container Apps - what the question set cannot express

## Fixed at creation

- **Zone redundancy and internal or external exposure of the environment.** Both force a new
  environment; neither is edited.
- **The environment's virtual network and subnet.** An environment is created into a subnet
  and cannot be moved to another.
- **The workload-profiles kind of the environment.** It is a different environment type from
  the legacy consumption-only one, and the two do not convert.
- **The app's name** (it forms the revision names and the default hostname) and **the
  environment's region.**

## Ordering

The identity, its roles on the registry (`AcrPull`) and on the vault, the network and the
delegated subnet, the environment, then the app - and after it every app that shares the
environment. The first revision pulls its image and
resolves its secrets *during creation*, so every role must already be effective: a role granted
at the same apply is usually not yet. The workspace before the environment's diagnostic setting.
An internal environment's private DNS zone before anything calls the app.

## Roles

A role on the app is a `wiring.role_assignments` entry with it as `to`. It is Azure RBAC on
the app - the control plane. Usually the deploying principal holds these alone, and the spec
then has no entry for the app. The roles the app's identity holds on what it calls are
entries with the app (or its user-assigned identity) as `from`.

## Pitfalls

**The first revision fails for want of a role.** An app created with a system-assigned identity
cannot hold `AcrPull` before it exists, and the pull fails; with a user-assigned identity whose
role was granted a moment ago it fails on propagation delay. The failure looks like a bad
image. Grant first, wait, then create the app - the reason the default is `user_assigned`.

**Bicep's ingress defaults are the open ones.** `ingressExternal` true, `ingressAllowInsecure`
true, target port 80; the Terraform module defaults to internal and HTTPS-only. Every ingress
decision is written.

**The subnet is delegated and exclusive.** It carries the delegation to
`Microsoft.App/environments`, at least a /27 for a workload-profiles environment, and is used by
nothing else. A subnet too small is discovered when the environment scales out and runs out of
addresses.

**An internal environment needs DNS the platform owns.** Its default domain
(`<unique>.<region>.azurecontainerapps.io`) resolves only through a private DNS zone the
platform links to the network; without it the apps run and nobody can call them.

**Two resource groups.** The platform creates a managed group for the environment's
infrastructure (named `ME_<environment>` unless set) and writes into it; nothing of the
deployment lives there and a policy that denies resources in unlisted groups can block the
environment.

**Logs by key or by diagnostic setting.** The `log-analytics` destination stores the workspace's
shared key in the environment; this set uses the `azure-monitor` destination and a diagnostic
setting instead. Console output then appears in the workspace's resource-specific tables only
once the setting exists.

**Scale to zero is a cold start.** A minimum of zero is the cheapest answer and the first
request after idle waits for a replica to start. Zone redundancy and a minimum of one do not go
together: spread needs two.

**A shared environment shares everything but the app.** Apps in one environment sit in the same
subnet, behind the same exposure (internal or public), with the same zone setting and peer
encryption, and their logs leave through the owner's one diagnostic setting; none of that can
differ between them, and neither can the region. Every replica of every app takes an address
from the one subnet, so a subnet sized for one app is undersized for three. The environment is
the owner's decision (`hosting_environment: own`); the second app's `hosting_environment: shared`
names the owner and nothing else about the environment. Removing the owner removes the
environment under every app in it, so the owner is the app that lives as long as the workload.

**Deprecated inputs in the Terraform environment module.** `internal_load_balancer_enabled`,
`infrastructure_subnet_id`, `zone_redundancy_enabled`, `workload_profile`, `peer_authentication_enabled`
and `peer_traffic_encryption_enabled` are deprecated for `vnet_configuration`, `zone_redundant`,
`workload_profiles`, `peer_authentication` and `peer_traffic_configuration`. The render uses
the new ones.

**Log category names are the platform's.** Checked against `az monitor diagnostic-settings
categories list --resource <environment id>` before a render.

## Not covered here, and why

Dapr, KEDA scale rules, jobs, dynamic sessions and session pools (sandboxed code execution),
custom domains and certificates, Easy Auth, health probes and volumes each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
