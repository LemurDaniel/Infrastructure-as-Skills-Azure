# Rendering a Static Web App as Bicep

Mapping from the question set to the app. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/static-web-app.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/web/static-site:<version>` | **0.9.6** | 2026-10-25 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `sku` | `'Free'` (default) / `'Standard'`; written |
| `preview_environments_enabled` | `stagingEnvironmentPolicy: 'Enabled'` / `'Disabled'` | Default **`'Enabled'`**; written |
| `public_network_access` | `publicNetworkAccess: 'Disabled'` / `'Enabled'` | Default `''` (unset): disabled only when a private endpoint is given |
| `private_endpoint_subnet` | `privateEndpoints: [ { service: 'staticSites', subnetResourceId } ]` | `service` defaults to `staticSites` |
| `deployment.private_dns_records` | no `privateDnsZoneGroup` on the endpoint under `policy` | |
| (the platform owns zones) | `createPrivateDnsZone: 'Disabled'` | Default **`'Enabled'`**: with a private endpoint the module creates a zone and needs `virtualNetworkResourceId`. Always written |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { userAssignedResourceIds }` | |
| `role_assignments` | `roleAssignments` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |
| (no diagnostics) | none | The module has no `diagnosticSettings` parameter; see the notes |

### The call

```bicep
module staticSite 'br/public:avm/res/web/static-site:0.9.6' = {
  name: 'static-web-app'
  params: {
    name: appName
    location: location
    tags: tags

    // decision: static-web-app.static_web_app.sku
    sku: 'Standard'
    // decision: static-web-app.static_web_app.preview_environments_enabled - the module default is Enabled
    stagingEnvironmentPolicy: 'Disabled'

    // decision: static-web-app.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    // the platform owns the zone, which carries the app's partition id
    createPrivateDnsZone: 'Disabled'
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'staticSites'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    managedIdentities: { userAssignedResourceIds: [ userAssignedIdentityId ] }
    roleAssignments: roleAssignments
    enableTelemetry: true
  }
}

output id string = staticSite.outputs.resourceId
output defaultHostname string = staticSite.outputs.defaultHostname
```

Compiles with `bicep build` against 0.9.6. The module's output list holds `name`, `resourceId`,
`defaultHostname`, `privateEndpoints` and the system identity's principal id, and **no partition
id**; the partition is read from the default hostname.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)).

## Authored rendering

The fallback. `Microsoft.Web/staticSites` with `sku` and `properties`:

| Decision | Property |
|---|---|
| `sku` | `sku: { name, tier }` |
| `preview_environments_enabled` | `properties.stagingEnvironmentPolicy` |
| `public_network_access` | `properties.publicNetworkAccess` |
| `managed_identity` | `identity: { type, userAssignedIdentities }` |
| private endpoint | `Microsoft.Network/privateEndpoints` with `groupIds: [ 'staticSites' ]` |
