# Rendering API Management as Bicep

Mapping from the question set to the instance. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/api-management.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/api-management/service:<version>` | **0.15.0** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide parameters

| Input | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module apiManagement 'br/public:avm/res/api-management/service:0.15.0' = {
  name: 'api-management'
  params: {
    name: apiManagementName
    location: location
    tags: tags

    // decision: api-management.service.publisher_name, publisher_email
    publisherName: publisherName
    publisherEmail: publisherEmail

    // decision: api-management.service.sku, capacity - the module default is Premium with 3 units
    sku: 'StandardV2'
    skuCapacity: 1
    availabilityZones: []

    managedIdentities: {
      systemAssigned: true
    }

    // decision: api-management.networking.network_integration
    virtualNetworkType: 'Internal'
    subnetResourceId: apimSubnetId
    // decision: api-management.networking.public_network_access
    publicNetworkAccess: 'Disabled'

    enableDeveloperPortal: false
    enableClientCertificate: false
    customProperties: customProperties

    // decision: api-management.access.caller_authentication, rate_limit_calls_per_minute
    policies: [
      {
        name: 'policy'
        format: 'rawxml'
        value: globalPolicy
      }
    ]

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'GatewayLogs' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = apiManagement.outputs.resourceId
```

`globalPolicy` is `loadTextContent('policies/global.xml')` with the tenant id and audience
substituted; the XML is the one in [terraform.md](terraform.md#the-global-policy). The audience is
an `open:` entry (app registrations are not rendered).

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy text is
matched on `validate-jwt` and `calls="600"`.

## Authored rendering

The fallback. `Microsoft.ApiManagement/service` with `sku: { name, capacity }` and `properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
