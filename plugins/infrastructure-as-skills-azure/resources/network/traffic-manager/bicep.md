# Rendering a Traffic Manager profile as Bicep

Mapping from the question set to `Microsoft.Network/trafficManagerProfiles`. General layout,
parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/traffic-manager.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/trafficmanagerprofile:<version>` | **0.4.0** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. Note the
registry path: `trafficmanagerprofile` in one word, unlike most Bicep modules.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

Not carried by the module: nothing from this question set. `allowedEndpointRecordTypes` and `lock`
are parameters the question set has no decision for - leave them unset.

### The call

```bicep
module trafficManager 'br/public:avm/res/network/trafficmanagerprofile:0.4.0' = {
  name: 'traffic-manager'
  params: {
    name: trafficManagerName
    location: 'global'
    tags: tags

    // decision: traffic-manager.profile.routing_method - forced by traffic_goal: failover; the module default is Performance
    trafficRoutingMethod: 'Priority'
    // decision: traffic-manager.profile.relative_dns_name (empty: the resource name)
    relativeName: trafficManagerName
    // decision: traffic-manager.profile.dns_ttl_seconds
    ttl: 60
    // decision: traffic-manager.profile.profile_status
    profileStatus: 'Enabled'
    // decision: traffic-manager.profile.traffic_view
    trafficViewEnrollmentStatus: 'Disabled'
    // decision: traffic-manager.profile.max_return - MultiValue only; the module default is 1
    maxReturn: 1

    // decision: traffic-manager.monitoring.monitor_protocol, monitor_port, monitor_path, expected_status_codes, probe_profile (standard) - the module default probes http:80/
    monitorConfig: {
      protocol: 'HTTPS'
      port: 443
      path: '/health'
      intervalInSeconds: 30
      timeoutInSeconds: 10
      toleratedNumberOfFailures: 3
      expectedStatusCodeRanges: [ { min: 200, max: 299 } ]
    }

    // decision: traffic-manager.endpoints.endpoints
    endpoints: [
      for e in endpoints: {
        name: e.name
        type: 'Microsoft.Network/trafficManagerProfiles/azureEndpoints'
        properties: {
          targetResourceId: e.targetResourceId
          endpointStatus: 'Enabled'
          priority: e.priority
          endpointLocation: e.location
        }
      }
    ]

    // decision: traffic-manager.access.role_assignments
    roleAssignments: []

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        // decision: traffic-manager.observability.diagnostic_categories
        logCategoriesAndGroups: [ { category: 'ProbeHealthStatusEvents' } ]
        // decision: traffic-manager.observability.metrics_enabled
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output id string = trafficManager.outputs.resourceId
output fqdn string = '${trafficManagerName}.trafficmanager.net' // the module has no fqdn output
```

Validated with `bicep build` against the published module, endpoints loop included. The module
outputs `name`, `resourceGroupName` and `resourceId` only; the FQDN for `wiring.dns_records` is
assembled from the relative name.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)):
`trafficRoutingMethod`, `relativeName`, `ttl`, `profileStatus`, `trafficViewEnrollmentStatus`,
`maxReturn`, every member of `monitorConfig`, the `endpoints` copy, `roleAssignments`, the
diagnostic categories. `traffic_goal` is marked `not_testable` (it pre-answers the method).

## Authored rendering

The fallback. `Microsoft.Network/trafficManagerProfiles` (`location: 'global'`) with
`properties.profileStatus`, `trafficRoutingMethod`, `dnsConfig: { relativeName, ttl }`,
`monitorConfig`, `endpoints[]` (the same shape as the module's parameter),
`trafficViewEnrollmentStatus` and `maxReturn`. Diagnostics are a `Microsoft.Insights/diagnosticSettings`
extension resource with `scope: trafficManager`; role assignments likewise. Validated with
`bicep build`.
