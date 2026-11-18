# Rendering a Key Vault as Bicep

Mapping from the question set to the vault. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/key-vault.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/key-vault/vault:<version>` | **0.14.2** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The Bicep
module is `Available`, unlike the Terraform one.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Parameter | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `privateDnsZoneGroup` on the endpoint | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module vault 'br/public:avm/res/key-vault/vault:0.14.2' = {
  name: 'key-vault'
  params: {
    name: vaultName
    location: location
    tags: tags

    // decision: key-vault.vault.sku - the module default is premium
    sku: 'standard'
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true

    // decision: key-vault.networking.public_network_access
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
      ipRules: []
    }
    privateEndpoints: [
      {
        name: privateEndpointName
        service: 'vault'
        subnetResourceId: privateEndpointSubnetId
        // private_dns_records: policy - no zone group, the platform policy writes the record
      }
    ]

    // decision: key-vault.security.enabled_for_services - the module default for
    // deployment is true
    enableVaultForDeployment: false
    enableVaultForDiskEncryption: false
    enableVaultForTemplateDeployment: false

    roleAssignments: roleAssignments

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'AuditEvent' }
          { category: 'AzurePolicyEvaluationDetails' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = vault.outputs.resourceId
output uri string = vault.outputs.uri
```

### Secret placeholders

The module requires a `value` for every secret, and a redeploy writes it as a **new version**,
so a placeholder passed through `secrets` replaces the real value on every deployment. The
render keeps placeholders out of the module and gives each one `@onlyIfNotExists()`, so it is
deployed once and never again over a value somebody set. The toolchain is assumed to be the
latest Bicep; there is no lookup of existing secrets, no parameter for one and no pipeline step:

```bicep
resource vaultRef 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: vaultName
  dependsOn: [ vault ]
}

@onlyIfNotExists()
resource placeholder 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = [for name in secretPlaceholders: {
  parent: vaultRef
  name: name
  properties: {
    value: 'placeholder - replace after deployment'
    contentType: 'placeholder'
  }
}]
```

The API version is looked up against the compiled module rather than recalled. A Bicep that
rejects the decorator is a toolchain to update, not a reason to write a lookup.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). How the
decorator shows in the compiled ARM is read from a compile, not recalled; the placeholder
resources are matched by that.

## Authored rendering

The fallback. A single `Microsoft.KeyVault/vaults` with `properties`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

`enablePurgeProtection` may only be `true` or omitted; ARM rejects an explicit `false`.
