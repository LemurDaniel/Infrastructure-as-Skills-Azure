# Rendering an automation account as Bicep

Mapping from the question set to `Microsoft.Automation/automationAccounts`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/automation-account.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/automation/automation-account:<version>` | **0.19.3** | 2026-11-01 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The MCR tag
list sorts as text, so `0.9.1` comes after `0.19.3` - sort by version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| (the account) | `name` | Assembled from the `aa` abbreviation, affix and workload; 6-50 characters |
| `deployment.private_dns_records` | `privateEndpoints[].privateDnsZoneGroup` | Left out under `policy` |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set. `linkedWorkspaceResourceId` and
`gallerySolutions` serve the retired Update Management and Change Tracking solutions and stay
unset; `runbooks`, `schedules`, `jobSchedules`, `webhooks`, `variables`, `credentials`,
`modules`, `powershell72Modules`, `python3Packages`, `hybridRunbookWorkerGroups` and
`sourceControlConfigurations` are content and stay unset; `lock` stays unset because
`deployment.resource_lock` does not list automation accounts.

### The call

```bicep
module automationAccount 'br/public:avm/res/automation/automation-account:0.19.3' = {
  name: 'automation-account'
  params: {
    name: automationAccountName
    location: location
    tags: tags

    // decision: automation-account.account.sku
    skuName: 'Basic'

    // decision: automation-account.networking.public_network_access - a string here, a bool on the resource
    publicNetworkAccess: 'Disabled'
    // decision: automation-account.security.local_authentication_disabled
    disableLocalAuth: true

    // decision: automation-account.identity.managed_identity
    managedIdentities: {
      userAssignedResourceIds: [ userAssignedIdentityId ] // decision: automation-account.identity.user_assigned_identity_ids
    }

    // decision: automation-account.networking.private_endpoint_subresources - one entry each
    privateEndpoints: [
      {
        service: 'Webhook'
        subnetResourceId: privateEndpointSubnetId // decision: automation-account.networking.private_endpoint_subnet
      }
      {
        service: 'DSCAndHybridWorker'
        subnetResourceId: privateEndpointSubnetId
      }
    ]

    diagnosticSettings: [
      {
        workspaceResourceId: logAnalyticsWorkspaceId // decision: automation-account.observability.diagnostic_workspace
        // decision: automation-account.observability.diagnostic_categories
        logCategoriesAndGroups: [
          { category: 'JobLogs' }
          { category: 'JobStreams' }
          { category: 'AuditEvent' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ] // decision: automation-account.observability.metrics_enabled
      }
    ]

    roleAssignments: [] // decision: automation-account.identity.role_assignments

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = automationAccount.outputs.resourceId
```

For `key_management: customer_managed` the call adds `customerManagedKey: { keyVaultResourceId,
keyName, userAssignedIdentityResourceId }`, the key id split into its vault and its name, without
`keyVersion`.

Validated with `bicep build` against the published module 0.19.3.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)):
`publicNetworkAccess` is `Disabled`, `disableLocalAuth` is `true`, one private endpoint per
sub-resource, the three log categories. `disableLocalAuth` is the one to assert on purpose -
the Terraform side spells it the other way round.

## Authored rendering

The fallback. `Microsoft.Automation/automationAccounts` with `properties.sku.name`,
`properties.publicNetworkAccess` and `properties.disableLocalAuth` - **both bools** on the
resource, where the module takes a string for public access - `identity` and
`properties.encryption { keySource: 'Microsoft.Keyvault', keyVaultProperties { keyvaultUri,
keyName }, identity { userAssignedIdentity } }`. Private endpoints are
`Microsoft.Network/privateEndpoints`, one per sub-resource (`groupIds: [ 'Webhook' ]`,
`[ 'DSCAndHybridWorker' ]`); diagnostics a `Microsoft.Insights/diagnosticSettings` scoped to the
account. Validated with `bicep build` (`Microsoft.Automation/automationAccounts@2023-11-01`).
