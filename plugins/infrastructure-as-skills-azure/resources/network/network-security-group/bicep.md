# Rendering a Network Security Group as Bicep

Mapping from the question set to the NSG. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/network-security-group.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/network-security-group:<version>` | **0.5.4** | 2026-10-23 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter | Note |
|---|---|---|
| (flow re-evaluation) | `flushConnection` | Default `false`; left, with its prerequisites in `notes.md` |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module nsg 'br/public:avm/res/network/network-security-group:0.5.4' = {
  name: 'network-security-group'
  params: {
    name: nsgName
    location: location
    tags: tags

    securityRules: concat(
      [
        // decision: network-security-group.rules.default_inbound - explicit, so it shows in the plan
        {
          name: 'deny-all-inbound'
          properties: {
            priority: 4096
            direction: 'Inbound'
            access: 'Deny'
            protocol: '*'
            sourceAddressPrefix: '*'
            sourcePortRange: '*'
            destinationAddressPrefix: '*'
            destinationPortRange: '*'
          }
        }
      ]
      baselineRules // by subnet_purpose
      explicitRules // from `rules`, always Allow
    )

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'NetworkSecurityGroupEvent' }
          { category: 'NetworkSecurityGroupRuleCounter' }
        ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = nsg.outputs.resourceId
```

Parameter and output spellings are read from the README of the pinned version. The output
`resourceId` is what the virtual-network set takes for a subnet's `networkSecurityGroupResourceId`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the deny rule
at 4096, every custom rule `Allow`, priorities unique.

## Authored rendering

The fallback. `Microsoft.Network/networkSecurityGroups` with `properties.securityRules`, each
with the rule members above. Rules as child resources and rules inline in the group's
properties are alternatives, not a pair: mixing them makes a redeploy remove one or the other.
