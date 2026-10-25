# Microsoft Defender for Cloud - what the question set cannot express

## It is a subscription setting

Plans, the security contact and the integration settings belong to the **subscription**; there is
no resource group and no resource to put them in. Three consequences:

- The deployment is at subscription scope (Bicep `targetScope = 'subscription'`; Terraform's
  `azurerm` provider for that subscription). A pipeline that deploys the workload into a resource
  group needs a second deployment, and a right at the subscription, for this.
- A plan applies to **every resource of its kind in the subscription**, the workload's and
  anyone else's. In a shared subscription the bill and the alerts are shared; in a vended
  application landing zone the subscription is the workload's, which is why this set is written for
  that case.
- Stages are separate subscriptions (guardrails, *Stages*), so each stage's subscription gets its
  own deployment of this set from its own stage file.

## Platform or deployment

In an application landing zone the platform assigns the Defender plans by policy and owns the
security contact; `defender_ownership: platform` (the default) renders **nothing**, and a plan the
workload needs that is not enabled is an `open:` entry for the platform team. Writing a plan the
policy also writes gives a plan that drifts on every run and a policy that turns off what the code
turned on. `defender_ownership: deployment` (forced for `landing_zone: standalone`) is for a
subscription nothing manages.

## What each plan costs, in shape

Every plan is a **paid** tier (`Standard`) with its own meter. No prices here - they change and
differ by region and agreement; the pricing page for the plan is read at the time of the decision.

| Plan | Billed per | What grows the bill |
|---|---|---|
| `VirtualMachines` (servers) | server per hour, by sub-plan P1/P2 | Number of servers, including stopped-not-deallocated ones; P2 is a multiple of P1 |
| `StorageAccounts` | storage account per month, plus per transaction | Accounts and request volume; malware scanning adds **per GB scanned**, sensitive-data discovery adds per account/data scanned |
| `KeyVaults` | per 10,000 operations | A vault read per request instead of once at start |
| `Arm` | per million management operations | Pipelines and automation that call the control plane a lot |
| `AppServices` | app instance (plan instance) per month | Scale-out instances |
| `Containers` | vCore per hour of the cluster nodes | Node count and size |
| `SqlServers`, `OpenSourceRelationalDatabases` | server per month | Number of servers |
| `CosmosDbs` | per 100 RU/s per hour | Provisioned throughput |
| `Api` | per API subscription tier, per million calls | Call volume |
| `CloudPosture` | per billable resource per month (servers, storage accounts, databases) | The number of resources in the subscription |

Foundational posture management (the free security score and recommendations) is on in every
subscription and is not a plan to enable.

The per-resource meters are why the default is **no plan**: a switch that bills per resource,
silently, for everything in the subscription is a decision the person confirms. The pattern proposes
the plans the spec's resources match - `VirtualMachines` for a VM, `StorageAccounts` for a storage
account, `KeyVaults` for a vault, `AppServices` for a web or function app, `Containers` for
AKS, `SqlServers` / `OpenSourceRelationalDatabases` / `CosmosDbs` for the databases - with their cost shape.

## Fixed at creation

Nothing is immutable: a plan can be switched to `Free` and back at any time. What lingers is data -
alerts, recommendations, scan results - and the **bill until the switch**, hourly or monthly by plan.
A sub-plan or tier change takes effect for the whole subscription at once.

## Ordering

Nothing in a workload depends on it, and it depends on nothing - except that malware scanning on
a storage account takes effect on accounts that exist when it is switched on **and** on later ones,
so the order against the storage account is free. The contact comes with the plans; a plan
without a contact raises alerts nobody reads.

## Pitfalls

**The Bicep module writes every plan as `Free` when `defenderPlans` is omitted.** The AVM
security-center pattern module defaults the list to twelve plans, all `Free`, which downgrades any
plan somebody enabled. The render always passes `defenderPlans` explicitly, and `[]` when no plan
is named (nothing is written).

**Unlisted does not mean off.** A plan the spec does not name is not touched. A plan removed from the
spec later is not switched back to `Free` by the Bicep render (it is not written at all); the
Terraform resource switches it to `Free` on destroy, because it owns the setting. The handover says
which.

**Two writers.** A policy that assigns plans, the portal's "Environment settings", and this template
fight each other. The ownership decision exists to name one.

**The contact is one object.** `securityContacts/default` is a single resource per subscription: a
second deployment from another repository replaces the first's emails.

**Auto-provisioning is retired.** The Log Analytics (MMA) agent and its automatic installation
setting are gone; what remains is the plan's sub-plan and extensions (agentless scanning, the Azure
Monitor agent through data collection rules), and the latter are not covered here.

**A cap stops the scan, not the upload.** `storage_malware_scan_cap_gb` bounds the monthly bill; files
above it are stored unscanned.

**Rights.** Writing a plan or the contact needs `Security Admin` (or `Contributor` / `Owner`) at the
subscription; the handover lists it with the scope.

## Not covered here, and why

Continuous export to a workspace or Event Hub, governance rules, custom security standards and
regulatory-compliance assignments, alert suppression, Defender for IoT and Microsoft Sentinel each
carry decisions of their own and have no question set yet; a request for one is said out loud, not
improvised.
