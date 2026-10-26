# Data collection rule - what the question set cannot express

## Fixed at creation

- **The kind.** `Linux`, `Windows`, `AgentDirectToStore`, `Direct` and `WorkspaceTransforms`
  are different rule shapes; changing one is a new rule and new associations.
- **The region** of the rule and of its endpoint. The endpoint must share the region of the
  machines that call it.
- **The immutable id.** The service assigns `immutableId` at creation; an application posting
  to the ingestion API addresses the rule by it, so a re-created rule breaks every sender until
  they are reconfigured.
- **The endpoint's kind** (`Linux` / `Windows`).

## Ordering

The workspace, then any custom table in it (`Custom-<Table>_CL` must exist before a rule
declares a stream into it, or the deployment fails on the data flow), then the identity and its
data roles for a direct-to-store rule, then the endpoint, then the rule, then the associations
on each machine - and the Azure Monitor agent on those machines, installed by the compute set or
by policy, which the rule cannot check. The transformation and stream files before the render.

## Pitfalls

**A rule collects nothing until a machine is associated.** The association is a resource on the
*machine* (`Microsoft.Insights/dataCollectionRuleAssociations` with the machine as scope), not an
input of either AVM module: the Terraform root renders
`azurerm_monitor_data_collection_rule_association` per machine from `associations`, Bicep an
extension resource with `scope:`. A rule that needs an endpoint needs a **second** association
per machine, named exactly `configurationAccessEndpoint`, carrying the endpoint and no rule;
without it the agent never fetches the configuration and the first text log never arrives.

**The two endpoint modules disagree on public access.** Terraform `Enabled`, Bicep `Disabled`.
A Bicep endpoint left at the default without an AMPLS rejects every agent; a Terraform one left
at the default is open where the posture says closed. Written on every call.

**Closed means through a private link scope, not through a private endpoint.** The endpoint
joins the platform's Azure Monitor Private Link Scope as a scoped resource; the machines resolve
it through the scope's DNS zones. The scope's access mode (`Open` / `PrivateOnly`) is the
platform's and decides whether an agent outside the scope still reaches the public service
endpoints at all.

**Counters are spelled per operating system.** `Processor(*)\% Processor Time` on Linux,
`\Processor(_Total)\% Processor Time` on Windows, and a specifier in the wrong dialect is
accepted at deployment and collects nothing. The `performance_counter_set` resolves per `kind`
at render; a custom counter is checked on a machine first.

**`Microsoft-Perf` and `Microsoft-InsightsMetrics` are two streams from one source.** The first
is the queryable `Perf` table, the second feeds Azure Monitor Metrics (guest metrics for a
metric alert). The default sends both; dropping the metrics stream saves nothing and removes
the near-real-time alert path.

**Syslog levels are a list, not a floor.** The service takes the explicit list of levels; the
render expands `syslog_min_level` upwards and renders `auth`/`authpriv` as a second data source
at `Info`, because a successful login is the row a review needs.

**A transformation can drop the row it is debugging.** `source | where ...` with a mistyped
column drops everything silently; the rule's `LogErrors` diagnostic category is where that
shows, which is why the set routes it. Transformations beyond 50 % of the ingested volume are
billed on the excess.

**A Windows Security log twice is a double bill.** Where Sentinel or Defender for Servers runs,
the platform's rule already collects it; `windows_security_events: none` is the default so a
workload rule does not duplicate it.

**The Terraform DCR module takes `Linux` and `Windows` only.** Its `kind` input is validated
against those two; a `Direct`, `AgentDirectToStore` or `WorkspaceTransforms` rule renders authored
on `azurerm` 5.x and the spec says so. The Bicep module has no `AgentDirectToStore` variant either.

**The Terraform DCR module's diagnostic setting cannot be verified offline.** The module
exposes `diagnostic_settings`; the category names (`LogErrors`, `LogTroubleshooting`) are
checked with `az monitor diagnostic-settings categories list --resource <rule id>` before a
render. The Bicep DCR module has **no `diagnosticSettings` parameter** (0.11.0) - the setting is
rendered authored beside the module call, `Microsoft.Insights/diagnosticSettings` with
`scope:` the rule. The rule has no metrics.

**`Direct` rules authorise senders by role on the rule.** An application posting to the
ingestion API needs `Monitoring Metrics Publisher` on the rule (or the endpoint); the role
assignment is wiring the pattern records in `role_assignments` of the module.

## Not covered here, and why

The Azure Monitor agent extension and its machines (the compute set), the AMPLS and its DNS
(the platform), custom tables and their retention (the workspace set), the Prometheus /
Container Insights / VM Insights data sources beyond naming the extension (product
configuration loaded from a file), `PlatformTelemetry` rules for Azure resource metrics, and
the legacy `Microsoft.Insights/diagnosticSettings` per resource (rendered by each resource set)
each carry decisions of their own; a request for one is said out loud, not improvised.
