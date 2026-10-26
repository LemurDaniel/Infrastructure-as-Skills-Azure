# Action group - what the question set cannot express

## Fixed at creation

- **The location.** An action group is created `global` and stays so; a regional group
  (data residency on notification metadata) is a different resource, not an edit.
- **Nothing else.** Every receiver, the short name and the enabled switch are updates in
  place - which is also the risk: whoever can write the group redirects every alert.

## Ordering

The targets of the receivers before the group: the Function App, the Logic App workflow,
the Event Hub, the Automation webhook and the Entra application of a secure webhook all
exist first, because the group holds their ids and callback URLs. The group before every
alert rule that names it. The e-mail confirmation after the deployment, by a person: an
e-mail or SMS receiver is created `NotActivated`, Azure sends a confirmation, and until it
is accepted the receiver is silent. The template cannot see that state and never will;
the handover says who confirms it.

## Pitfalls

**A person's address is the wrong answer to the one required question.** `on_call_email` is
a shared mailbox or a distribution list. A personal address works on the day it is set and
fails the day the person leaves, silently, because the confirmation stays accepted.

**The common alert schema is off in both modules.** Azure's default, and the reason a
receiver written against a metric alert's payload breaks on the first log alert. The set
writes `use_common_alert_schema = true` on every receiver type that has the switch; SMS,
voice, push and ITSM have none.

**A secure webhook needs a Graph consent the template cannot give.** `use_aad_auth` makes
Azure Monitor obtain a token for the target application; that application must grant the
`Azure Monitor Alerts` service principal access first (the documented PowerShell against
Microsoft Graph). Without it the call is rejected with no alert and no error anyone sees.
A plain webhook (`url_secret`) for a Teams or Slack incoming webhook has no such step and
no upgrade path.

**Credential-bearing URLs stay out of state and out of the spec.** The Terraform module
sends `service_uri`, `http_trigger_url`, `callback_url` and the runbook `service_uri`
through AzAPI's write-only `sensitive_body` (Terraform 1.11 or later when any is set) and
keeps a hash; Bicep takes them as `securestring`. The render reads them from the target
resource (`list_keys`, `listCallbackUrl()`), never from a literal. Everything else -
addresses, phone numbers - is plaintext in state; the backend is encrypted and read access
to it is narrow.

**An ARM role receiver mails users, not groups.** Every *user* holding the built-in role on
the subscription at firing time, by the role's GUID; members of a group assigned the role
and service principals are not reached. Only built-in roles are accepted.

**SMS is rate-limited.** No more than one SMS per number every five minutes, and a number
can opt out by replying; the opt-out is invisible to the template.

**The short name is twelve characters and shows up as the sender.** The render takes it
from the workload; two systems with the same first twelve characters are told apart only
by the full name in the e-mail body.

**No logs and no metrics.** `Microsoft.Insights/actionGroups` has no diagnostic
categories and no platform metrics, so the set has no `observability` group. Whether a
notification was delivered is read from the alert's history in the portal or from the
`AlertsManagementResources` Resource Graph table, not from a diagnostic setting.

## Not covered here, and why

Alert rules (the alert-rule set), alert processing rules (suppression windows, routing by
tag), the `incidentReceivers` of the preview API versions (Azure Monitor's incident
management, not in the stable API the Terraform module targets), voice and mobile-app push
receivers (personal channels, against the shared-mailbox rule), and the ITSM connection or
Automation runbook themselves each carry decisions of their own; a request for one is said
out loud, not improvised.
