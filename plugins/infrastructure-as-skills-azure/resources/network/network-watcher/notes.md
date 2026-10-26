# Network Watcher - what the question set cannot express

## The watcher is Azure's; the flow log is the decision

Network Watcher is created by Azure: one per region per subscription, named
`NetworkWatcher_<region>` in the resource group `NetworkWatcherRG`, the first time a virtual
network is deployed in that region. A region holds exactly one. So the resource that a workload
decides about is not the watcher but its children - above all the **virtual network flow log**,
which records every flow in a network (allowed and denied, with or without a security group) to a
storage account and, through Traffic Analytics, into the workspace. NSG flow logs, the older form
attached to a security group, are retired for new deployments and this set does not render them.

`ownership: platform` therefore renders the flow logs as children of the existing watcher, in
`NetworkWatcherRG`; `ownership: deployment` creates the watcher first, and only where the
auto-creation is disabled by policy and no watcher exists.

## Fixed at creation

- **The flow log's target and name.** A flow log is bound to one network, subnet or interface; a
  different target is a new flow log. A target can carry only one flow log.
- **The watcher's region and name.** The auto-created one is never renamed or moved.
- **Nothing else.** Retention, analytics, the storage account and the interval are edited in place.

## Ordering

1. The virtual network - which also makes Azure create the region's watcher under `platform`
2. The storage account (general-purpose v2, no hierarchical namespace, same region and
   subscription as the watcher) and the workspace
3. Under `deployment`: the watcher; under `platform`: a data source / `existing` read of
   `NetworkWatcher_<region>` - a plan on a subscription that never held a network in that region
   fails here, because the watcher does not exist yet
4. The flow logs, one per target, deployed **into the watcher's resource group**
5. Connection monitors, after the agents on their sources

Deletion runs the other way; a flow log whose storage account was deleted first stays in a failed
state until it is removed.

## Pitfalls

**The flow log lives in `NetworkWatcherRG`, not in the deployment's group.** It is a child of the
watcher. The Bicep render deploys it at `scope: resourceGroup('NetworkWatcherRG')`, the Terraform
module takes the watcher's id as `parent_id`; the deploying identity needs Contributor-level rights
on that group, which a landing zone grants per subscription but a narrowly scoped pipeline identity
may not have. The handover names it.

**One flow log per target, and a second deployment collides.** Two renders - two workloads in one
subscription, or a stage rerun under a new name - that both log the same network fail on the
second with a conflict. The flow log's name is derived from the target for that reason.

**The modules differ in how analytics is switched.** Bicep enables Traffic Analytics by the presence
of `workspaceResourceId` and takes the workspace's id alone; Terraform needs the workspace's
**GUID** (`workspace_id`), its region and its resource id, all three, and `enabled = true` inside
`traffic_analytics`. `traffic_analytics: false` is the absence of the workspace in Bicep and
`enabled = false` in Terraform.

**Retention is on the storage blobs, not in the workspace.** `retention_days` governs the raw files;
the analysed data follows the workspace's retention (`deployment.log_retention_days`). 0 means
forever. The Bicep module's default is **365**, the guardrail's 30 - written on every call.

**The storage account has constraints.** Same region as the watcher and the network, same
subscription, general-purpose v2, **no hierarchical namespace**, and the account's network rules
must allow the trusted service (`Microsoft.Network`) or the writes fail silently. A flow log pointed
at a hardened logging account that forgot the bypass collects nothing.

**NSG flow logs are gone for new ones.** A request for "NSG flow logs" is answered with a VNet flow
log on the network that holds the group; the data is a superset. A repository that already has
`azurerm_network_watcher_flow_log` on an NSG keeps it - the migration is a decision, not a side
effect of a render.

**The Terraform module cannot create the watcher.** It reads it (`data "azurerm_network_watcher"`)
and needs its id and name as inputs; `ownership: deployment` renders an authored
`azurerm_network_watcher` beside the module and passes its id in. The Bicep module does the
opposite: it always declares the watcher resource (an idempotent PUT on the existing one when
deployed into `NetworkWatcherRG` under its name), and the child module `network-watcher/flow-log`
is the one that only references it.

**Connection monitors need an agent.** A source VM without the Network Watcher extension (or an Arc
machine without the Azure Monitor agent) produces a monitor that reports nothing. The extension is
the compute set's.

## Not covered here, and why

NSG flow logs, packet captures, VPN troubleshooting, the topology and connection troubleshoot
tools, Traffic Analytics' own alert rules and the storage account's lifecycle policy each belong to
operations or to another set; a request for one is said out loud, not improvised.
