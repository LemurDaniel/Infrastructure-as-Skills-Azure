# Rendering an Application Gateway as Bicep

Mapping from the question set to the gateway. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/application-gateway.bicep
```

## With the AVM modules

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/application-gateway:<version>` | **0.10.0** | 2026-10-25 |
| `br/public:avm/res/network/application-gateway-web-application-firewall-policy:<version>` | **0.3.0** | 2026-10-25 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact versions. The firewall
is a **separate module**: the gateway takes the policy's id in `firewallPolicyResourceId`.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Parameters no decision covers

| Decision | Parameter |
|---|---|
| `deployment.module_telemetry` | `enableTelemetry` |
| `context.tags` | `tags` |

### The call

```bicep
module wafPolicy 'br/public:avm/res/network/application-gateway-web-application-firewall-policy:0.3.0' = {
  name: 'waf-policy'
  params: {
    name: wafPolicyName
    location: location
    tags: tags
    // decision: application-gateway.gateway.waf_mode
    policySettings: {
      mode: 'Prevention'
      state: 'Enabled'
    }
    // decision: application-gateway.gateway.waf_rule_set, waf_bot_protection
    managedRules: wafManagedRules
    enableTelemetry: true
  }
}

module applicationGateway 'br/public:avm/res/network/application-gateway:0.10.0' = {
  name: 'application-gateway'
  params: {
    name: applicationGatewayName
    location: location
    tags: tags

    // decision: application-gateway.gateway.waf_enabled
    sku: 'WAF_v2'
    firewallPolicyResourceId: wafPolicy.outputs.resourceId
    // decision: application-gateway.gateway.capacity_min, capacity_max - the module default is a fixed 2
    autoscaleMinCapacity: 2
    autoscaleMaxCapacity: 10
    // decision: application-gateway.gateway.zone_redundant
    availabilityZones: [ 1, 2, 3 ]

    gatewayIPConfigurations: [
      {
        name: 'gateway-ip'
        properties: {
          subnet: { id: gatewaySubnetId }
        }
      }
    ]

    managedIdentities: {
      userAssignedResourceIds: userAssignedIdentityIds
    }

    // decision: application-gateway.networking.tls_policy, http2_enabled
    sslPolicyType: 'Predefined'
    sslPolicyName: 'AppGwSslPolicy20220101S'
    enableHttp2: true

    // frontends, listeners, pools, probes, rules and certificates: the pattern's wiring
    frontendIPConfigurations: frontendIpConfigurations
    frontendPorts: frontendPorts
    httpListeners: httpListeners
    backendAddressPools: backendAddressPools
    backendHttpSettingsCollection: backendHttpSettings
    probes: probes
    requestRoutingRules: requestRoutingRules
    sslCertificates: sslCertificates

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'ApplicationGatewayAccessLog' }
          { category: 'ApplicationGatewayFirewallLog' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = applicationGateway.outputs.resourceId
```

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy is
its own nested deployment.

## Authored rendering

The fallback. `Microsoft.Network/applicationGateways` with `properties`, and
`Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies`.

What each decision renders to - the property and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.
