# Rendering Communication Services as Bicep

Mapping from the question set to the resources. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/communication-services.bicep
```

## With the AVM modules

| | Module | Documented against | Resolved |
|---|---|---|---|
| Communication service | `br/public:avm/res/communication/communication-service:<version>` | **0.6.0** | 2026-10-26 |
| Email service (+ domains, sender usernames) | `br/public:avm/res/communication/email-service:<version>` | **0.4.5** | 2026-10-26 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The
e-mail module carries the domain and the sender usernames as nested parameters; the separate
`email-service/domain` child module (0.1.0) is not needed.

### Decision -> module parameter

| Decision | Module | Parameter | Note |
|---|---|---|---|
| `location` | both | `location: 'global'` | Module default `'global'`; written |
| `data_location` | both | `dataLocation` | **Required**, immutable; identical on both |
| `email` | email | the module call exists; `domains: [ { name, domainManagement } ]` | `'AzureManaged'` with name `AzureManagedDomain`; `'CustomerManaged'` with the domain name |
| `custom_domain_name` | email | `domains[].name` | |
| `sender_usernames` | email | `domains[].senderUsernames: [ { name, username, displayName } ]` | |
| `user_engagement_tracking` | email | `domains[].userEngagementTracking: 'Disabled'` / `'Enabled'` | A string, not a bool |
| (linking) | communication | `linkedDomains: [ '<email service id>/domains/<name>' ]` | The domain id |
| `public_network_access` | communication | `publicNetworkAccess` | `'Enabled'` / `'Disabled'` / `'SecuredByPerimeter'`; unset by default; written |
| `network_security_perimeter` | - | authored `Microsoft.Network/networkSecurityPerimeters/profiles/resourceAssociations` | Only when set |
| `managed_identity`, `user_assigned_identity_ids` | communication | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `role_assignments` | both | `roleAssignments` | `'Communication and Email Service Owner'` is configurable by name |
| `local_authentication_disabled` | communication | `disableLocalAuth` | Unset by default; written |
| `diagnostic_*`, `metrics_enabled` | communication | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | The e-mail service has no diagnostic setting of its own |
| `deployment.module_telemetry` | both | `enableTelemetry` | |
| `context.tags` | both | `tags` | |

### The call

```bicep
module email 'br/public:avm/res/communication/email-service:0.4.5' = {
  name: 'email-service'
  params: {
    name: '${communicationName}-email'
    location: 'global'
    tags: tags
    dataLocation: 'Europe' // decision: communication-services.service.data_location
    // decision: communication-services.service.email, custom_domain_name, sender_usernames, user_engagement_tracking
    domains: [
      {
        name: 'AzureManagedDomain'
        domainManagement: 'AzureManaged'
        userEngagementTracking: 'Disabled'
        senderUsernames: [
          { name: 'DoNotReply', username: 'DoNotReply', displayName: 'DoNotReply' }
        ]
      }
    ]
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

module communication 'br/public:avm/res/communication/communication-service:0.6.0' = {
  name: 'communication-service'
  params: {
    name: communicationName
    location: 'global'
    tags: tags
    dataLocation: 'Europe' // decision: communication-services.service.data_location
    linkedDomains: [ '${email.outputs.resourceId}/domains/AzureManagedDomain' ]
    // decision: communication-services.networking.public_network_access - Enabled without a perimeter
    publicNetworkAccess: 'Enabled'
    // decision: communication-services.security.local_authentication_disabled
    disableLocalAuth: true
    // decision: communication-services.identity.managed_identity - none; `{ systemAssigned: true }` for recordings in storage
    managedIdentities: {}
    roleAssignments: roleAssignments
    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'Usage' }
          { category: 'AuthOperational' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = communication.outputs.resourceId
```

With `email: none` the e-mail module and `linkedDomains` are omitted. For a custom domain the
entry is `{ name: customDomainName, domainManagement: 'CustomerManaged', ... }` and the domain's
verification records are read from the deployed resource for the DNS owner.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); `linkedDomains`
is an expression over the e-mail module's output and is matched on its text.

## Authored rendering

The fallback. `Microsoft.Communication/communicationServices@2025-09-01` with `location: 'global'`,
`identity` and `properties`:

| Decision | Property |
|---|---|
| `data_location` | `properties.dataLocation` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `local_authentication_disabled` | `properties.disableLocalAuth` |
| (linking) | `properties.linkedDomains` |
| `email`, `custom_domain_name`, `user_engagement_tracking`, `sender_usernames` | `Microsoft.Communication/emailServices` with child `domains` (`properties.domainManagement`, `userEngagementTracking`) and `domains/senderUsernames` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` scoped to the communication service |
