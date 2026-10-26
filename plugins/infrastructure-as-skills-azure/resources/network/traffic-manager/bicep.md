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

| Decision | Parameter | Note |
|---|---|---|
| `traffic_goal` | - | Pre-answers `routing_method`; nothing of its own in the call |
| `routing_method` | `trafficRoutingMethod` | Module default **`'Performance'`**; written |
| `relative_dns_name` | `relativeName` | The module falls back to `name` when unset; written anyway |
| `dns_ttl_seconds` | `ttl` | Module default 60; written |
| `profile_status` | `profileStatus` | Module default `'Enabled'`; written |
| `traffic_view` | `trafficViewEnrollmentStatus` | `'Enabled'` / `'Disabled'`; written |
| `max_return` | `maxReturn` | Module default 1; written |
| `monitor_protocol`, `monitor_port`, `monitor_path`, `expected_status_codes`, `probe_profile` | `monitorConfig: { protocol, port, path, intervalInSeconds, timeoutInSeconds, toleratedNumberOfFailures, expectedStatusCodeRanges: [ { min, max } ] }` | Module default is **`http` on port 80 at `/`**; the whole object is written. `standard`: 30 / 10 / 3; `fast`: 10 / 9 / 3 |
| `endpoints` | `endpoints: [ { name, type, properties: { targetResourceId or target, endpointStatus, priority, weight, endpointLocation, geoMapping, minChildEndpoints } } ]` | One array; the kind is the ARM `type`: `Microsoft.Network/trafficManagerProfiles/azureEndpoints`, `/externalEndpoints`, `/nestedEndpoints`. The parameter is typed from the resource schema, so a misspelt property fails `bicep build` |
| `role_assignments` | `roleAssignments: [ { principalId, roleDefinitionIdOrName: 'Traffic Manager Contributor', principalType } ]` | |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { category } ], metricCategories: [ { category: 'AllMetrics' } ] } ]` | Without either list the module collects everything; both are written |
| `location` | `location: 'global'` | Module default; written |
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
the decision, so every decision above is observable in `tests/*.armtest.yaml`
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
