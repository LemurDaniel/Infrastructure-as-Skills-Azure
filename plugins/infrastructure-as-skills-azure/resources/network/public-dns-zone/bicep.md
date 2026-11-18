# Rendering a public DNS zone as Bicep

Mapping from the question set to `Microsoft.Network/dnsZones`. General layout, parameters and
naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/public-dns-zone.bicep
```

## With the AVM module

| Module | Documented against | Resolved |
|---|---|---|
| `br/public:avm/res/network/dns-zone:<version>` | **0.6.2** | 2026-10-26 |

Resolve the current version and re-read the README parameters before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. Pin the exact version. The module
carries more than its Terraform counterpart: DNSSEC, the lock and role assignments are
parameters here.

### Decision -> module parameter

What each decision renders to - the parameter and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Parameter | Note |
|---|---|---|
| `deployment.resource_lock` | `lock: { kind: 'CanNotDelete' }` | In the stages the deployment names |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `context.tags` | `tags` | |

`ds`, `ptr`, `soa` and `srv` are parameters the question set has no decision for - leave them
unset. `ns` is the delegation list and nothing else: the zone's own NS record set at `@` is
Azure's and is not written.

### The call

```bicep
module publicDnsZone 'br/public:avm/res/network/dns-zone:0.6.2' = {
  name: 'public-dns-zone'
  params: {
    // decision: public-dns-zone.zone.zone_name
    name: zoneName
    location: 'global'
    tags: tags

    // decision: public-dns-zone.records.record_sets - record_ttl_seconds is the ttl
    a: [
      { name: 'www', ttl: 3600, aRecords: [ { ipv4Address: '203.0.113.10' } ] }
    ]
    aaaa: []
    cname: [
      { name: 'app', ttl: 3600, cnameRecord: { cname: 'app.azurefd.net' } }
    ]
    // decision: public-dns-zone.records.verification_records - TXT, filled from wiring.dns_records
    txt: [
      { name: 'asuid.www', ttl: 3600, txtRecords: [ { value: [ 'ABCDEF0123456789' ] } ] }
    ]
    mx: [
      { name: '@', ttl: 3600, mxRecords: [ { preference: 10, exchange: 'mail.example.com.' } ] }
    ]
    caa: [
      { name: '@', ttl: 3600, caaRecords: [ { flags: 0, tag: 'issue', value: 'letsencrypt.org' } ] }
    ]
    // decision: public-dns-zone.zone.child_zone_delegations - an NS record set per child zone
    ns: [
      for child in childZoneDelegations: { name: child.name, ttl: 3600, nsRecords: map(child.nameServers, ns => { nsdname: ns }) }
    ]

    // decision: public-dns-zone.security.dnssec
    enableDnsSec: true

    // decision: public-dns-zone.access.role_assignments
    roleAssignments: []
    // deployment.resource_lock: production
    lock: { kind: 'CanNotDelete' }

    enableTelemetry: false // deployment.module_telemetry: disabled
  }
}

output nameServers array = publicDnsZone.outputs.nameServers // registrar_owner enters these
output id string = publicDnsZone.outputs.resourceId
```

Validated with `bicep build` against the published module, records, delegation loop and DNSSEC
included. `nameServers` is what the handover lists for the delegation.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is
the decision, so every decision in render-map.yaml is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): `name`,
`location`, the record arrays per type, `enableDnsSec`, `roleAssignments`, `lock`. The `ns` loop
compiles to a `copy` whose expression names the parameter; `registrar_owner` is a handover entry
and is marked `not_testable`.

## Authored rendering

The fallback. `Microsoft.Network/dnsZones` (`location: 'global'`, `properties.zoneType: 'Public'`)
with the record children `Microsoft.Network/dnsZones/A`, `/AAAA`, `/CNAME`, `/TXT`, `/MX`, `/CAA`,
`/NS` (each `properties.TTL` and the typed `ARecords` / `CNAMERecord` / `TXTRecords` / `MXRecords` /
`caaRecords` / `NSRecords`, or `targetResource.id` for an alias), the DNSSEC child
`Microsoft.Network/dnsZones/dnssecConfigs@2023-07-01-preview` named `default`, role assignments
and the lock as extension resources with `scope`. Validated with `bicep build`.
