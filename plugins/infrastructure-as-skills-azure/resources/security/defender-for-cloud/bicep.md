# Rendering Defender for Cloud as Bicep

Mapping from the question set to the subscription's plans and contact. General layout, parameters
and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
Nothing here renders when `defender_ownership` is `platform`.

```bash
bicep build --stdout main.defender.bicep
```

The template's `targetScope` is `subscription`.

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/ptn/security/security-center:<version>` | **0.3.0** | 2026-10-25 |

A **pattern** module (`Available`), not a resource module: it writes the subscription's pricings and
the contact, and optionally standards, automations and governance rules (not used here). Resolve the
current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

**Always pass `defenderPlans`.** Left out, the module writes twelve plans (`VirtualMachines`,
`SqlServers`, `AppServices`, `StorageAccounts`, `SqlServerVirtualMachines`, `KeyVaults`, `Arm`,
`OpenSourceRelationalDatabases`, `Containers`, `CosmosDbs`, `CloudPosture`, `Api`) all as `Free`
- which downgrades any plan somebody enabled. `[]` writes none (verified in the compiled
deployment).

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter | Note |
|---|---|---|
| (storage) | `subPlan: 'DefenderForStorageV2'` on the `StorageAccounts` entry | |
| `enforce` | *not used* | Prevents child scopes overriding; for management group scope, not rendered |
| `deployment.module_telemetry` | `enableTelemetry` | |

### The call

```bicep
targetScope = 'subscription'

param securityContactEmails string

module defender 'br/public:avm/ptn/security/security-center:0.3.0' = {
  name: 'defender-for-cloud'
  params: {
    // decision: defender-for-cloud.security.plans - omitting this writes every plan as Free
    defenderPlans: [
      // decision: defender-for-cloud.security.servers_plan
      { name: 'VirtualMachines', pricingTier: 'Standard', subPlan: 'P1' }
      {
        name: 'StorageAccounts'
        pricingTier: 'Standard'
        subPlan: 'DefenderForStorageV2'
        extensions: [
          // decision: defender-for-cloud.security.storage_malware_scanning / storage_malware_scan_cap_gb
          { name: 'OnUploadMalwareScanning', isEnabled: 'True', additionalExtensionProperties: { CapGBPerMonth: '1000' } }
          // decision: defender-for-cloud.security.storage_sensitive_data_discovery
          { name: 'SensitiveDataDiscovery', isEnabled: 'False' }
        ]
      }
      { name: 'KeyVaults', pricingTier: 'Standard' }
    ]
    // decision: defender-for-cloud.identity.*
    securityContactProperties: {
      emails: securityContactEmails
      isEnabled: true
      notificationsByRole: { state: 'On', roles: [ 'Owner' ] }
      notificationsSources: [
        { sourceType: 'Alert', minimalSeverity: 'Medium' }
      ]
    }
    enableTelemetry: true
  }
}

output configuredPlans array = defender.outputs.configuredDefenderPlans
```

The call was built with `bicep build` against the version in the table. Outputs are `name`
(always `Security`) and `configuredDefenderPlans`. The deploying identity needs `Security Admin`
(or `Contributor` / `Owner`) at the subscription; `az deployment sub create` is the verb.

An extension that is off is written with `isEnabled: 'False'` here, so a later spec change
switches it off rather than leaving it on.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the plan names and
tiers in `defenderPlans`, the contact in `securityContactProperties`. What a plan costs is
`not-testable` with that reason.

## Authored rendering

The fallback - or a repository that already renders pricings this way. At subscription scope:

```bicep
@batchSize(1)
resource pricing 'Microsoft.Security/pricings@2024-01-01' = [for plan in plans: {
  name: plan.name
  properties: {
    pricingTier: 'Standard'
    subPlan: plan.?subPlan
    extensions: plan.?extensions
  }
}]

resource contact 'Microsoft.Security/securityContacts@2023-12-01-preview' = {
  name: 'default'
  properties: {
    emails: securityContactEmails
    isEnabled: true
    notificationsByRole: { state: 'On', roles: [ 'Owner' ] }
    notificationsSources: [ { sourceType: 'Alert', minimalSeverity: 'Medium' } ]
  }
}
```

The pricings are written one after another (`@batchSize(1)`): concurrent writes to different
plans of one subscription conflict.
