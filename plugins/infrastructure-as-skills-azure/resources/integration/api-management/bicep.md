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

| Decision | Parameter | Note |
|---|---|---|
| `publisher_name`, `publisher_email` | `publisherName`, `publisherEmail` | Required |
| `sku` | `sku` | `Basic`, `BasicV2`, `Consumption`, `Developer`, `Premium`, `PremiumV2`, `Standard`, `StandardV2`. Module default **`Premium`**; written |
| `capacity` | `skuCapacity` | Module default **3**; written |
| `zone_redundant` | `availabilityZones` | Premium/PremiumV2 only; `[1, 2, 3]` or `[]` |
| `additional_regions` | `additionalLocations` | Premium only |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `caller_authentication`, `rate_limit_calls_per_minute` | `policies: [ { name: 'policy', format: 'rawxml', value } ]` | The service-level policy; the same XML as the Terraform reference |
| `developer_portal` | `enableDeveloperPortal` | Module default `false`; written |
| `apis`, `products` | `apis`, `products`, `apiVersionSets`, `backends`, `namedValues`, `subscriptions` | Content of the API team; the names and the backend only |
| `network_integration` | `virtualNetworkType` | `'None'` / `'External'` / `'Internal'`; default `'None'`; written |
| `apim_subnet` | `subnetResourceId` | |
| `public_ip_address` | `publicIpAddressResourceId` | Standard static IPv4; classic tiers in a network |
| `public_network_access` | `publicNetworkAccess` | `'Enabled'` / `'Disabled'`; unset by default; written |
| `private_endpoint_subnet` | `privateEndpoints: [ { subnetResourceId, service: 'Gateway' } ]` | Tiers with private endpoint support only |
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `legacy_protocols_disabled` | `customProperties: { 'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls10': 'False', ... }` | The module sets a block of these by default; every key is written so a release cannot move it. The key list is in the README |
| `client_certificate_required` | `enableClientCertificate` | Default `false`; written |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName, principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
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
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy text is
matched on `validate-jwt` and `calls="600"`.

## Authored rendering

The fallback. `Microsoft.ApiManagement/service` with `sku: { name, capacity }` and `properties`:

| Decision | Property |
|---|---|
| `publisher_*` | `properties.publisherName`, `publisherEmail` |
| `zone_redundant` | `zones` (top level, beside `properties`) |
| `network_integration` | `properties.virtualNetworkType`, `virtualNetworkConfiguration.subnetResourceId` |
| `public_ip_address` | `properties.publicIpAddressId` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `legacy_protocols_disabled` | `properties.customProperties` |
| `client_certificate_required` | `properties.enableClientCertificate` |
| `managed_identity` | `identity` (top level) |
| global policy | child `policies/policy` |
| `apis`, `products` | child `apis`, `products` |
