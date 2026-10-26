# Azure observability resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table — the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| Log Analytics, workspace, log retention | `log-analytics-workspace/questions.yaml` | [notes](log-analytics-workspace/notes.md) |
| Application Insights, APM, traces, appinsights | `application-insights/questions.yaml` | [notes](application-insights/notes.md) - always workspace-based |
| action group, Aktionsgruppe, who is notified, on-call, Bereitschaft, Benachrichtigung, webhook, Teams channel | `action-group/questions.yaml` | [notes](action-group/notes.md) - the who of an alert; global, no logs or metrics |
| alert, alert rule, metric alert, log alert, scheduled query, Service Health, activity log alert, Alarm, Schwellwert, Benachrichtigung bei | `alert-rule/questions.yaml` | [notes](alert-rule/notes.md) - one set for metric, log query and activity log alerts, chosen by kind |
| data collection rule, DCR, data collection endpoint, DCE, Azure Monitor agent, AMA, syslog, performance counters, Windows event log, custom log, Leistungsdaten, Logdateien sammeln | `data-collection-rule/questions.yaml` | [notes](data-collection-rule/notes.md) - the rule and its endpoint; the association is wiring per machine |
| dashboard, workbook | *not yet written* | — |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) — the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), where
   `observability_ownership` already decided whether this resource is created at all
2. [iac-rendering](../../core/iac-rendering/SKILL.md) — the spec into Terraform or Bicep

## True for the whole family

**Most deployments should reference a workspace, not create one.** A workspace per
deployment fragments exactly the correlation an incident needs — the question "what else
was happening at 03:14" cannot be answered across six workspaces. `create` is for an
isolated environment with no platform workspace to point at, and the deployment set
settles that before this resource is reached.

**Retention is the cost decision, and it is billed twice.** Ingestion is charged per
gigabyte on the way in; retention beyond the free period is charged per gigabyte per month
after that. The failure mode is not an expensive workspace — it is someone turning
logging off to stop the bill, which costs more the first time it matters.

**Deleting a workspace is soft for 14 days** and the name stays reserved for that period.
A recreate with the same name inside the window fails or recovers the old one, which is
confusing in both directions; `terraform destroy` followed immediately by `apply` is where
this shows up.
