# Application Insights - what the question set cannot express

## Fixed at creation

- **The application type.** Changing it replaces the component; the old telemetry stays in the
  workspace under the old resource id.
- **The workspace link** can be changed, but a component moved to another workspace leaves its
  history behind in the first.
- **The name** within the resource group.

## Ordering

The workspace, then the component, then (for a closed component) its entry in the platform's
Azure Monitor Private Link Scope, then the role assignments, then the applications that send to
it. The application gets the **connection string** as an output of the component, passed as an
app setting (`APPLICATIONINSIGHTS_CONNECTION_STRING`) - a reference, not a secret in the
template; with local authentication off the string alone is not enough to send: the
application's identity holds `Monitoring Metrics Publisher` on the component and its
`APPLICATIONINSIGHTS_AUTHENTICATION_STRING` is `Authorization=AAD` (system-assigned) or
`Authorization=AAD;ClientId=<client id>` (user-assigned). Settings and role are rendered with
the application; only the code that reads them is the application's.

## Pitfalls

**Retention is the workspace's.** A workspace-based component stores its data in the workspace
and follows the workspace's retention, per-table and daily cap. The component's own retention
property is written by the render from the workspace's value so the two never disagree, but it
is not a lever. The modules differ on it (Terraform 90 days, Bicep 365).

**Closing the component without the scope silently drops telemetry.** With ingestion disabled
and no Azure Monitor Private Link Scope reachable from the application's network, the SDK sends
nothing and reports nothing. The check is a test event after deployment, not a plan.

**One scope, many resources.** The AMPLS is shared by every monitoring resource in the network
and has an access mode (`Open` or `PrivateOnly`) of its own: `Open` lets a machine on the
network still send to workspaces outside the scope. Its settings are the platform's.

**Local auth off breaks old SDKs.** The instrumentation key alone is no longer accepted; the
SDK has to authenticate with Entra ID, and the application's identity needs `Monitoring Metrics
Publisher`. A browser SDK cannot, which is the named departure.

**Sampling is applied twice.** The SDK samples, then the component samples what is left; two
sets of 50% is 25%. The SDK's adaptive sampling keeps failures, which the component's cannot.

**The daily cap drops data.** Past the cap telemetry is discarded until the next day, with a
notification (unless disabled). An alert on ingestion volume is the usual better answer.

**IP addresses.** The modules' defaults differ (Terraform masks, Bicep stores); the decision
document names it for the data-protection review.

## Not covered here, and why

Alerts and action groups, availability tests, workbooks and dashboards, the profiler's linked
storage, continuous export and the classic standalone component each carry decisions of their
own and have no question set; a request for one is said out loud, not improvised.
