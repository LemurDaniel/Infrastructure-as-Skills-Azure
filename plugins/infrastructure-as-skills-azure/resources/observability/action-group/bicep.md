# Rendering an action group as Bicep

Mapping from the question set to the group. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/action-group.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/insights/action-group:<version>` | **0.8.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
targets `Microsoft.Insights/actionGroups@2024-10-01-preview` and so also carries
`incidentReceivers`, which this set does not render.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Parameter | Note |
|---|---|---|
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
var onCallReceiver = {
  name: 'oncall'
  emailAddress: onCallEmail
  useCommonAlertSchema: true
}
var additionalEmailReceivers = [
  for r in emailReceivers: {
    name: r.name
    emailAddress: r.emailAddress
    useCommonAlertSchema: true
  }
]
var secureWebhookReceivers = [
  for r in webhookReceivers: {
    name: r.name
    serviceUri: r.serviceUri
    useCommonAlertSchema: true
    useAadAuth: true
    objectId: r.objectId
    identifierUri: r.identifierUri
  }
]

module actionGroup 'br/public:avm/res/insights/action-group:0.8.0' = {
  name: 'action-group'
  params: {
    name: actionGroupName
    // decision: action-group.placement.location - a global resource
    location: 'global'
    tags: tags

    // decision: action-group.notification.short_name - empty derives it from the workload, 12 characters
    groupShortName: take(empty(shortName) ? workload : shortName, 12)
    // decision: action-group.notification.enabled
    enabled: actionGroupEnabled

    // decision: action-group.notification.on_call_email, email_receivers, common_alert_schema -
    // the module default of useCommonAlertSchema is false
    emailReceivers: concat([onCallReceiver], additionalEmailReceivers)
    // decision: action-group.notification.sms_receivers
    smsReceivers: []
    // decision: action-group.notification.webhook_receivers, webhook_authentication - secure webhook
    webhookReceivers: secureWebhookReceivers
    // decision: action-group.notification.azure_function_receivers
    azureFunctionReceivers: []
    // decision: action-group.notification.logic_app_receivers
    logicAppReceivers: []
    // decision: action-group.notification.event_hub_receivers
    eventHubReceivers: []
    // decision: action-group.notification.arm_role_receivers - built-in roles by GUID
    armRoleReceivers: []
    // decision: action-group.notification.automation_runbook_receivers
    automationRunbookReceivers: []
    // decision: action-group.notification.itsm_receivers
    itsmReceivers: []

    // decision: action-group.identity.role_assignments
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output actionGroupId string = actionGroup.outputs.resourceId
```

A `for` expression is not allowed inside a module parameter, hence the `var`s. Built with
`bicep build` against 0.8.0 on 2026-10-26.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so `groupShortName` (an expression text with `take(`), `enabled`, `location`,
each receiver array and `useCommonAlertSchema: true` inside it are observable in
`tests/*.armtest.yaml` ([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).
A `securestring` receiver URL is a parameter reference in the template, matched by name, never
by value.

## Authored rendering

The fallback. `Microsoft.Insights/actionGroups@2023-01-01`, `location: 'global'`, with
`properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
