# Rendering a Load Balancer as Bicep

Mapping from the question set to the balancer. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/load-balancer.bicep
```

## With the AVM module

`br/public:avm/res/network/load-balancer:<version>` - the primary rendering. Documented against
**0.8.0** (resolved 2026-10-25); resolve the current version and re-read its README parameters before
rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version.
Status: Available.

**The module creates the public IP** from `frontendIPConfigurations[].publicIPAddressConfiguration`
(it takes an existing one in `publicIPAddressResourceId`). A rule and a probe refer to their pool,
probe and frontend by **name** (`backendAddressPoolName`, `probeName`, `frontendIPConfigurationName`),
so the names in the call must match. The Bicep and Terraform modules **disagree on defaults**: the
Terraform module defaults a rule to 3389 to 3389 and `enable_tcp_reset` to `false`; both are written.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `sku` | `skuName: 'Standard'`, `skuTier: 'Regional'` | Module default; written |
| `zone_redundant` | `frontendIPConfigurations[].availabilityZones` (and `publicIPAddressConfiguration.availabilityZones`) | `[1, 2, 3]` or `[]` |
| `frontend_exposure` | private: `subnetResourceId`; public: `publicIPAddressConfiguration` | One frontend per entry |
| `frontend_subnet` | `frontendIPConfigurations[].subnetResourceId` | |
| `private_ip_allocation`, `private_ip_address` | `frontendIPConfigurations[].privateIPAddress` | Set means static; unset means dynamic |
| `public_ip_zone_redundant` | `publicIPAddressConfiguration: { availabilityZones, skuName: 'Standard', skuTier: 'Regional', publicIPAllocationMethod: 'Static' }` | |
| `backend_pools` | `backendAddressPools: [ { name, loadBalancerBackendAddresses } ]` | A pool whose members are a scale set's joins from the scale set |
| `health_probe_protocol`, `health_probe_interval_seconds`, `health_probe_unhealthy_threshold` | `probes: [ { name, protocol, port, intervalInSeconds, numberOfProbes, requestPath } ]` | `requestPath` only with `'Http'` / `'Https'` |
| `tcp_reset`, `load_distribution`, `floating_ip` | `loadBalancingRules[].enableTcpReset`, `.loadDistribution`, `.enableFloatingIP` | |
| `rules` | `loadBalancingRules: [ { name, frontendIPConfigurationName, protocol, frontendPort, backendPort, backendAddressPoolName, probeName } ]` | Wiring: filled by the pattern; both ports always stated |
| `inbound_nat_rules` | `inboundNatRules` | Empty |
| `outbound_snat`, `outbound_allocated_ports` | `outboundRules: [ { name, frontendIPConfigurationName, backendAddressPoolName, allocatedOutboundPorts } ]`; `loadBalancingRules[].disableOutboundSnat: true` | Only with the rule |
| `diagnostic_*`, `metrics_enabled` | `diagnosticSettings: [ { workspaceResourceId, metricCategories: [ { category: 'AllMetrics' } ] } ]` | |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

### The call

```bicep
module loadBalancer 'br/public:avm/res/network/load-balancer:0.8.0' = {
  name: 'load-balancer'
  params: {
    name: loadBalancerName
    location: location
    tags: tags

    // decision: load-balancer.balancer.sku
    skuName: 'Standard'
    skuTier: 'Regional'

    // decision: load-balancer.networking.frontend_exposure, frontend_subnet, private_ip_allocation, private_ip_address
    // decision: load-balancer.balancer.zone_redundant
    frontendIPConfigurations: [
      {
        name: 'frontend'
        subnetResourceId: frontendSubnetId
        privateIPAddress: privateIpAddress
        availabilityZones: [ 1, 2, 3 ]
      }
    ]

    // decision: load-balancer.networking.backend_pools
    backendAddressPools: [
      for pool in backendPools: {
        name: pool.name
      }
    ]

    // decision: load-balancer.networking.health_probe_protocol, health_probe_interval_seconds, health_probe_unhealthy_threshold
    probes: [
      for probe in probes: {
        name: probe.name
        protocol: 'Tcp'
        port: probe.port
        intervalInSeconds: 5
        numberOfProbes: 2
      }
    ]

    // decision: load-balancer.networking.rules, tcp_reset, load_distribution, floating_ip
    loadBalancingRules: [
      for rule in rules: {
        name: rule.name
        frontendIPConfigurationName: 'frontend'
        protocol: rule.protocol
        frontendPort: rule.frontendPort
        backendPort: rule.backendPort
        backendAddressPoolName: rule.pool
        probeName: rule.probe
        loadDistribution: 'Default'
        enableFloatingIP: false
        enableTcpReset: true
        idleTimeoutInMinutes: 4
      }
    ]

    // decision: load-balancer.networking.inbound_nat_rules - none
    inboundNatRules: []

    diagnosticSettings: [
      {
        workspaceResourceId: diagnosticWorkspaceId
        metricCategories: [ { category: 'AllMetrics' } ]
      }
    ]
    enableTelemetry: true
  }
}

output id string = loadBalancer.outputs.resourceId
```

With `frontend_exposure: public` the frontend entry carries
`publicIPAddressConfiguration: { name: publicIpName, skuName: 'Standard', skuTier: 'Regional', publicIPAllocationMethod: 'Static', availabilityZones: [ 1, 2, 3 ] }` in place of `subnetResourceId` and
`privateIPAddress`. With `outbound_snat: outbound_rule` the call gains
`outboundRules: [ { name: 'outbound', frontendIPConfigurationName: 'frontend', backendAddressPoolName: '<pool>', allocatedOutboundPorts: 1024 } ]` and every rule on that frontend `disableOutboundSnat: true`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every decision above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)); the loops compile to a
`copy` whose expression text names the literal.

## Authored rendering

The fallback. `Microsoft.Network/loadBalancers` with `properties`, and `Microsoft.Network/publicIPAddresses`:

| Decision | Property |
|---|---|
| `sku`, `zone_redundant` | `sku: { name, tier }`; `properties.frontendIPConfigurations[].zones` (top-level of the entry) |
| `frontend_exposure`, `private_ip_*` | `properties.frontendIPConfigurations[].properties: { subnet: { id }, privateIPAllocationMethod, privateIPAddress }` or `{ publicIPAddress: { id } }` |
| `backend_pools` | `properties.backendAddressPools[]` |
| `health_probe_*` | `properties.probes[].properties: { protocol, port, requestPath, intervalInSeconds, numberOfProbes }` |
| `rules`, `tcp_reset`, `load_distribution`, `floating_ip` | `properties.loadBalancingRules[].properties: { protocol, frontendPort, backendPort, frontendIPConfiguration: { id }, backendAddressPool: { id }, probe: { id }, enableTcpReset, loadDistribution, enableFloatingIP, disableOutboundSnat }` |
| `inbound_nat_rules` | `properties.inboundNatRules[]` |
| `outbound_snat` | `properties.outboundRules[].properties: { protocol, allocatedOutboundPorts, backendAddressPool: { id }, frontendIPConfigurations: [ { id } ] }` |
