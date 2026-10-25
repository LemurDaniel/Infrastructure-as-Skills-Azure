# Rendering Front Door as Bicep

Mapping from the question set to the profile. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/front-door.bicep
```

Front Door Standard and Premium are resources of the **CDN profile** (`Microsoft.Cdn/profiles`).
The dedicated `avm/res/network/front-door` module is for the retired classic Front Door and is
**Deprecated** in the index: it is not used.

## With the AVM modules

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/cdn/profile:<version>` | **0.20.0** | 2026-10-25 |
| `br/public:avm/res/network/front-door-web-application-firewall-policy:<version>` | **0.3.3** | 2026-10-25 |

Resolve the current versions and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact versions. The firewall
policy is a **separate module** in Bicep: the profile's `securityPolicies` bind it by id.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `sku` | `'Standard_AzureFrontDoor'` / `'Premium_AzureFrontDoor'`; **required, no default**; written |
| `response_timeout_seconds` | `originResponseTimeoutSeconds` | **Module default 60** (Terraform 120); written |
| `managed_identity`, `user_assigned_identity_ids` | `managedIdentities: { systemAssigned, userAssignedResourceIds }` | |
| `origins`, `origin_connection` | `originGroups: [ { name, origins: [ { name, hostName, sharedPrivateLinkResource } ] } ]` | The private-link connection arrives *pending* |
| `forwarding_protocol`, `https_redirect`, `caching` | `afdEndpoints[].routes[]: { forwardingProtocol, httpsRedirect, cacheConfiguration }` | Route default for the protocol is `MatchRequest`; written |
| `custom_domains`, `certificate_source`, `minimum_tls_version` | `customDomains: [ { name, hostName, certificateType, minimumTlsVersion } ]` | `'ManagedCertificate'` / `'CustomerCertificate'`; `'TLS12'` |
| `waf_enabled`, `waf_mode`, `waf_managed_rules`, `waf_rate_limit_per_minute` | policy module `policySettings`, `managedRules`, `customRules`, plus the profile's `securityPolicies` | The policy `sku` must match the profile's; managed rules need Premium |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module wafPolicy 'br/public:avm/res/network/front-door-web-application-firewall-policy:0.3.3' = {
  name: 'front-door-waf'
  params: {
    name: wafPolicyName
    // decision: front-door.security.* - the policy's sku must match the profile's
    sku: 'Premium_AzureFrontDoor'
    policySettings: {
      mode: 'Prevention'
    }
    managedRules: wafManagedRules
    customRules: wafCustomRules
    enableTelemetry: true
    tags: tags
  }
}

module frontDoor 'br/public:avm/res/cdn/profile:0.20.0' = {
  name: 'front-door'
  params: {
    name: frontDoorName
    location: 'global'
    tags: tags

    // decision: front-door.profile.sku - required, no module default
    sku: 'Premium_AzureFrontDoor'
    // decision: front-door.profile.response_timeout_seconds
    originResponseTimeoutSeconds: 60

    originGroups: originGroups
    afdEndpoints: afdEndpoints
    customDomains: customDomains
    securityPolicies: [
      {
        name: 'waf'
        wafPolicyResourceId: wafPolicy.outputs.resourceId
        associations: securityPolicyAssociations
      }
    ]

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        logCategoriesAndGroups: [
          { category: 'FrontDoorAccessLog' }
          { category: 'FrontDoorHealthProbeLog' }
          { category: 'FrontDoorWebApplicationFirewallLog' }
        ]
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = frontDoor.outputs.resourceId
```

The member names of `originGroups`, `afdEndpoints` and `securityPolicies` are read from the
README for the pinned version.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)). The policy is
its own nested deployment.

## Authored rendering

The fallback. `Microsoft.Cdn/profiles` with `sku: { name }` and `properties`, and
`Microsoft.Network/FrontDoorWebApplicationFirewallPolicies`:

| Decision | Property |
|---|---|
| `response_timeout_seconds` | `properties.originResponseTimeoutSeconds` |
| `origins` | child `originGroups` and `originGroups/origins` |
| routes, endpoints | child `afdEndpoints` and `afdEndpoints/routes` |
| `custom_domains` | child `customDomains` with `properties.tlsSettings` |
| WAF | the policy's `properties.policySettings`, `managedRules`, `customRules`; child `securityPolicies` |
