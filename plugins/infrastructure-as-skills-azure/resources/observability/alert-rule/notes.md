# Alert rule - what the question set cannot express

## Fixed at creation

- **The kind.** A metric alert, a scheduled query rule and an activity log alert are three
  resource types; changing `kind` is a delete and a create under a new name.
- **The scope type of a metric alert.** A single-resource rule cannot become a multi-resource
  one in place: `targetResourceType` and the criteria type change together, which is a
  re-create.
- **The region of a log query rule.** The rule's `location` is immutable; a workspace that
  moves takes its rules with it as new resources.

## Ordering

The action group before every rule (the rule holds its id). The watched resources before a
metric alert - the service validates the metric name against the resource type at creation,
and a scope that does not exist yet fails the deployment, not the evaluation. The workspace
before a log query rule, and the identity with `Log Analytics Reader` on that workspace before
the rule's first evaluation, or the first run fails and the failure is a log entry nobody
watches. The query file before the render: a missing `queries/<rule>.kql` fails `file()` /
`loadTextContent()` at render.

## Pitfalls

**Both modules default severity to 3.** Informational, which most views and processing rules
filter out; a rule left at the default is one nobody sees. The set defaults to 2 and writes it.

**The Bicep metric alert defaults to a fifteen-minute window and the subscription as scope.**
`windowSize: 'PT15M'` and `scopes: [subscription().id]` - a call that forgets the scope creates
a subscription-wide rule that fails validation on the metric or, worse, watches everything.
Both are written.

**A multi-resource metric alert needs the type and region.** The Bicep module's criteria are
`MultipleResourceMultipleMetricCriteria` in every example; with it `targetResourceType` and
`targetResourceRegion` are mandatory and every scope must share them. The render reads both off
the first scope id and refuses a mixed list.

**Mute and auto-mitigate are mutually exclusive on a log query rule.** The service rejects
`muteActionsDuration` together with `autoMitigate: true`; a mute duration forces
auto-mitigation off, and a muted rule then stays open until a person or a processing rule
closes it.

**A log query rule without an identity runs as whoever deployed it.** The pipeline principal,
usually - whose rights change, after which the rule fails silently. The set defaults to a
user-assigned identity with `Log Analytics Reader`; the role assignment is wiring the pattern
renders, and the rule's `Monitoring Metrics Publisher` is not needed for a workspace scope.

**Dynamic thresholds need history.** A dynamic metric alert on a new resource fires on nothing
for days while it learns; on a resource with a weekly pattern it learns the wrong band in the
first week. `static` is the default for that reason.

**The query is content and the service validates it at deployment.** A typo in the KQL fails
the deployment of the rule, not the render; `skipQueryValidation` exists and is never set,
because an invalid query that deploys is a rule that never fires.

**The Service Health alert is subscription-scoped and should exist once per subscription.**
Two deployments in one subscription each rendering one is two notifications per incident; the
pattern checks the platform profile before adding it.

**No logs and no metrics.** None of the three types has diagnostic categories or platform
metrics; the set has no `observability` group. A rule's own health is read from the
`AlertsManagementResources` Resource Graph table and, for a log query rule, from its failure
notifications.

**Terraform has no AVM module for two of the three kinds.** Metric alerts and scheduled query
rules are `Proposed` in the Terraform index; they render authored on `azurerm` 5.x
(`azurerm_monitor_metric_alert`, `azurerm_monitor_scheduled_query_rules_alert_v2`) and the spec
records `implementation: authored`, `source: forced`, `forced_by: no AVM module for <type>`. The
activity log alert has one, AzAPI-only, which the Terraform root mixes with the two authored
resources in one module.

## Not covered here, and why

Alert processing rules (suppression, routing), smart detection and Application Insights
availability tests (web tests with their own alert type), Prometheus rule groups, the classic
log search alerts (API `2018-04-16`, deprecated), log-to-metric rules (`kind: LogToMetric`) and
the `SimpleLogAlert` kind each carry decisions of their own and have no question set; a request
for one is said out loud, not improvised.
