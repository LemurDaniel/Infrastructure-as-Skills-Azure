# Rendering an Azure Bastion as Bicep

Mapping from the question set to the Bastion host. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/bastion.bicep
```

## With the AVM module

`br/public:avm/res/network/bastion-host:<version>` - the primary rendering. Documented against
**0.8.2** (resolved 2026-10-25); resolve the current version and re-read its README parameters before
rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.
Status: Available.

**The module takes the virtual network's id, not the subnet's**: it looks up `AzureBastionSubnet` in it
by its fixed name (`virtualNetworkResourceId`; the Terraform module takes the subnet id). It creates the
public IP through `publicIPAddressObject` unless `bastionSubnetPublicIpResourceId` names one, and skips
it with `enablePrivateOnlyBastion`.

**Two decisions the module does not carry** - gaps in the sense of
[avm.md](../../../core/iac-rendering/references/avm.md#gaps-what-the-module-does-not-carry):

- **`native_client` is fixed on.** The module sets `enableTunneling` to `true` for `Standard` and for
  `Premium` without session recording, and has no parameter for it. A spec with `native_client: false`
  on `Standard` therefore renders the Bastion **authored** (below) with `implementation: authored`,
  `source: forced`, `forced_by: avm/res/network/bastion-host fixes tunneling on`, or records the value
  actually deployed (`true`) as `forced`. The Terraform module carries it (`tunneling_enabled`).
- **`metrics_enabled` is not in the module's diagnostic setting** (logs only). The metrics go in a
  second `Microsoft.Insights/diagnosticSettings` on the existing host, as below.

**The modules disagree on defaults:** file copy (Terraform `false`, Bicep `true`) and the zones
(Terraform all three, Bicep none); both are written.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `admin_access` | `enablePrivateOnlyBastion` | `true` for `private_network`; Premium. The public IP is then not created |
| `sku` | `skuName` | `'Developer'` / `'Basic'` / `'Standard'` / `'Premium'`; module default `'Basic'` - written |
| `zone_redundant` | `availabilityZones`; `publicIPAddressObject.availabilityZones` | `[1, 2, 3]` or `[]`; module default none. `Developer` has none |
| `scale_units` | `scaleUnits` | Module default `2`; the module forces `2` on Basic and Developer |
| `bastion_subnet` | `virtualNetworkResourceId` | The vnet; the module finds `AzureBastionSubnet`. `Developer` uses the same parameter |
| `public_ip_zone_redundant` | `publicIPAddressObject: { name, skuName: 'Standard', publicIPAllocationMethod: 'Static', availabilityZones }` | |
| `shareable_link` | `enableShareableLink` | |
| `native_client` | **not carried** | see above |
| `ip_connect` | `enableIpConnect` | |
| `file_copy` | `enableFileCopy` | Module default `true` - written `false` |
| `copy_paste` | `disableCopyPaste` | Inverted |
| `session_recording` | `enableSessionRecording` | Premium |
| `diagnostic_categories` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ] } ]` | |
| `metrics_enabled` | **not carried** | a second diagnostic setting, below |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module bastion 'br/public:avm/res/network/bastion-host:0.8.2' = {
  name: 'bastion'
  params: {
    name: bastionName
    location: location
    tags: tags

    // decision: bastion.bastion.sku
    skuName: 'Standard'
    // decision: bastion.bastion.zone_redundant
    availabilityZones: [ 1, 2, 3 ]
    // decision: bastion.bastion.scale_units
    scaleUnits: 2

    // decision: bastion.bastion.admin_access, bastion.networking.bastion_subnet
    enablePrivateOnlyBastion: false
    virtualNetworkResourceId: virtualNetworkId
    publicIPAddressObject: {
      name: publicIpName
      skuName: 'Standard'
      publicIPAllocationMethod: 'Static'
      availabilityZones: [ 1, 2, 3 ]
    }

    // decision: bastion.security.shareable_link
    enableShareableLink: false
    // decision: bastion.security.ip_connect
    enableIpConnect: false
    // decision: bastion.security.file_copy - the module defaults to true
    enableFileCopy: false
    // decision: bastion.security.copy_paste
    disableCopyPaste: false
    // decision: bastion.security.session_recording
    enableSessionRecording: false
    // decision: bastion.security.native_client - not carried by the module, which sets tunneling on for Standard

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [ { category: 'BastionAuditLogs' } ]
      }
    ]
    enableTelemetry: true
  }
}

// decision: bastion.observability.metrics_enabled - the module's diagnostic setting carries no metrics
resource bastionHost 'Microsoft.Network/bastionHosts@2025-01-01' existing = {
  name: bastionName
}

resource bastionMetrics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${bastionName}-metrics'
  scope: bastionHost
  properties: {
    workspaceId: diagnosticWorkspaceId
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
  dependsOn: [ bastion ]
}

output id string = bastion.outputs.resourceId
```

With `admin_access: private_network` the call is `skuName: 'Premium'` and
`enablePrivateOnlyBastion: true`, and `publicIPAddressObject` is dropped. With `sku: Developer` it has
`availabilityZones: []` and no `publicIPAddressObject`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above except the two gaps is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). `native_client` is
marked `# not-testable:` with the module's fixed value as the reason, or asserted on the authored
resource if the render departs from the module; the metrics setting is a plain resource in the
compiled template.

## Authored rendering

The fallback, and the render for `native_client: false` on `Standard`.
`Microsoft.Network/bastionHosts` with `properties`, and `Microsoft.Network/publicIPAddresses`:

| Decision | Property |
|---|---|
| `sku`, `zone_redundant` | `sku: { name }`; `zones` (top level; none for `Developer`) |
| `scale_units` | `properties.scaleUnits` |
| `bastion_subnet`, `admin_access` | `properties.ipConfigurations[].properties: { subnet: { id }, publicIPAddress: { id }, privateIPAllocationMethod: 'Dynamic' }`; `properties.enablePrivateOnlyBastion`; `Developer`: `properties.virtualNetwork.id` and no `ipConfigurations` |
| `shareable_link`, `native_client`, `ip_connect`, `file_copy`, `copy_paste`, `session_recording` | `properties.enableShareableLink`, `.enableTunneling`, `.enableIpConnect`, `.enableFileCopy`, `.disableCopyPaste` (inverted), `.enableSessionRecording` - the switches exist from `Standard` upward |
| public address | `Microsoft.Network/publicIPAddresses` with `sku: { name: 'Standard' }`, `properties.publicIPAllocationMethod: 'Static'`, `zones` |
| diagnostics | `Microsoft.Insights/diagnosticSettings` on the host with `logs: [ { category: 'BastionAuditLogs', enabled: true } ]` and `metrics: [ { category: 'AllMetrics', enabled: true } ]` |
