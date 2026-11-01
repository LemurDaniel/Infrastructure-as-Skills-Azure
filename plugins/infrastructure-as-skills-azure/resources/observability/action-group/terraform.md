# Rendering an action group as Terraform

Mapping from the question set to the group. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-insights-actiongroup/azurerm` | **v0.1.0** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.0`; the module is
at its first release.

**AzAPI only**: no `azurerm` requirement at all. It takes `parent_id` (the resource group's id)
and requires `azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.5` and Terraform `>= 1.9` - **`>= 1.11`
as soon as a webhook, function, Logic App or runbook receiver is set**, because those URLs go
through AzAPI's write-only `sensitive_body`. The resource type is
`Microsoft.Insights/actionGroups@2023-01-01`, the stable API; `incidentReceivers` of the preview
versions has no input.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Input | Note |
|---|---|---|
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "action_group" {
  source  = "Azure/avm-res-insights-actiongroup/azurerm"
  version = "~> 0.1.0"

  name      = data.naming_name.action_group.name
  parent_id = data.azurerm_resource_group.this.id
  # decision: action-group.placement.location - a global resource
  location = "Global"

  # decision: action-group.notification.short_name - empty derives it from the workload, 12 characters
  short_name = substr(coalesce(var.short_name, var.workload), 0, 12)
  # decision: action-group.notification.enabled
  enabled = var.action_group_enabled

  # decision: action-group.notification.on_call_email, email_receivers, common_alert_schema -
  # the module default of use_common_alert_schema is false
  email_receivers = merge(
    { oncall = { name = "oncall", email_address = var.on_call_email, use_common_alert_schema = true } },
    { for k, v in var.email_receivers : k => { name = k, email_address = v, use_common_alert_schema = true } }
  )
  # decision: action-group.notification.sms_receivers
  sms_receivers = {}
  # decision: action-group.notification.webhook_receivers, webhook_authentication - secure webhook
  webhook_receivers = {
    for k, v in var.webhook_receivers : k => {
      name                    = k
      service_uri             = v.service_uri
      use_common_alert_schema = true
      use_aad_auth            = true
      object_id               = v.object_id
      identifier_uri          = v.identifier_uri
    }
  }
  # decision: action-group.notification.azure_function_receivers
  azure_function_receivers = {}
  # decision: action-group.notification.logic_app_receivers
  logic_app_receivers = {}
  # decision: action-group.notification.event_hub_receivers
  event_hub_receivers = {}
  # decision: action-group.notification.arm_role_receivers - built-in roles by GUID
  arm_role_receivers = {}
  # decision: action-group.notification.automation_runbook_receivers
  automation_runbook_receivers = {}
  # decision: action-group.notification.itsm_receivers
  itsm_receivers = {}

  # decision: action-group.identity.role_assignments
  role_assignments = var.role_assignments

  enable_telemetry = true
  tags             = local.tags
}

output "action_group_id" { value = module.action_group.resource_id }
```

`var.email_receivers` is `map(string)` (key → address), `var.webhook_receivers` a map of
`{ service_uri, object_id, identifier_uri }` whose `service_uri` comes from a secret variable or
a data source, never a literal. Validated with `terraform validate` against v0.1.0 on
2026-10-26 (azurerm 5.11 in the root).

### Tests

`mock_provider "azapi"`, `"modtm"` (and `"azurerm"` for the root's data sources). The module
exposes **`resource_id` only** - no `resource` output, by design, because the bodies carry
addresses and URLs - so no decision of this set is observable from the plan: every one carries
`# not-testable: <key> - the action group module exposes no attribute; the call is the review`.
What a plan does observe is the root's own wiring: `substr(...)` of the short name as a local,
`length(var.on_call_email) > 0`, and that no receiver URL is a literal (a `sensitive` variable).

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

The authored resource stores every URL in state in plaintext, which is the reason the module
path is primary.
