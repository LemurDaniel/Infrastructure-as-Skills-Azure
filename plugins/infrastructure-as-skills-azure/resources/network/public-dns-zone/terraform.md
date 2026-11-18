# Rendering a public DNS zone as Terraform

Mapping from the question set to the public DNS zone. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-dnszone/azurerm` | **v0.2.1** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.1`.

**`azurerm`-based**: it takes `resource_group_name` (a name) and requires
`azurerm >= 3.71, < 5.0`, `modtm ~> 0.3`, `random ~> 3.5`, Terraform `~> 1.5` - a root calling it
cannot be on `azurerm` 5.x. It has no `location` input (the zone is `global` inside the module),
no lock, no role assignments, no diagnostics and no DNSSEC: the first three it simply lacks, the
last is rendered beside it (below). The root's provider set is the union with the other modules;
the DNSSEC child needs `azapi`.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.resource_lock` | **not carried by the module** | An authored `azurerm_management_lock` on the zone's id in the stages the deployment names |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

`srv_records` and `ptr_records` are inputs the question set has no decision for - leave them
unset. The record shapes differ per type: `txt_records.<k>.records` is a **map** of `{ value }`,
`mx_records.<k>.records` a map of `{ preference, exchange }`, `caa_records.<k>.record` a map of
`{ flags, tag, value }` with `flags` a **string**, `cname_records.<k>.record` a single string,
`a_records` / `aaaa_records` / `ns_records` a list of strings.

### The call

```hcl
locals {
  # every record of the module repeats the zone and the group; one local keeps them in step
  record_set_defaults = { resource_group_name = var.resource_group_name, zone_name = var.zone_name }
}

module "public_dns_zone" {
  source  = "Azure/avm-res-network-dnszone/azurerm"
  version = "~> 0.2.1"

  # decision: public-dns-zone.zone.zone_name
  name                = var.zone_name
  resource_group_name = var.resource_group_name

  # decision: public-dns-zone.records.record_sets - one map per type; record_ttl_seconds is the ttl
  a_records = {
    www = merge(local.record_set_defaults, { name = "www", ttl = 3600, records = ["203.0.113.10"] })
  }
  aaaa_records = {}
  cname_records = {
    app = merge(local.record_set_defaults, { name = "app", ttl = 3600, record = "app.azurefd.net" })
  }
  # decision: public-dns-zone.records.verification_records - TXT, filled from wiring.dns_records
  txt_records = {
    asuid_www = merge(local.record_set_defaults, { name = "asuid.www", ttl = 3600, records = { v = { value = "ABCDEF0123456789" } } })
  }
  mx_records = {
    apex = merge(local.record_set_defaults, { name = "@", ttl = 3600, records = { m10 = { preference = 10, exchange = "mail.example.com." } } })
  }
  caa_records = {
    apex = merge(local.record_set_defaults, { name = "@", ttl = 3600, record = { le = { flags = "0", tag = "issue", value = "letsencrypt.org" } } })
  }
  # decision: public-dns-zone.zone.child_zone_delegations - an NS record set per child zone
  ns_records = {
    for k, c in var.child_zone_delegations : k => merge(local.record_set_defaults, { name = c.name, ttl = 3600, records = c.name_servers })
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

# decision: public-dns-zone.security.dnssec - not carried by the module; the signing config is a child resource
resource "azapi_resource" "dnssec" {
  type      = "Microsoft.Network/dnsZones/dnssecConfigs@2023-07-01-preview"
  name      = "default"
  parent_id = module.public_dns_zone.resource_id
  body      = {}
}

# decision: public-dns-zone.access.role_assignments - not carried by the module
resource "azurerm_role_assignment" "zone" {
  for_each             = var.role_assignments
  scope                = module.public_dns_zone.resource_id
  role_definition_name = "DNS Zone Contributor"
  principal_id         = each.value.principal_id
  principal_type       = each.value.principal_type
}

output "name_servers" { value = module.public_dns_zone.name_servers } # registrar_owner enters these
output "id" { value = module.public_dns_zone.resource_id }
```

Validated with `terraform validate` (registry, v0.2.1, `azurerm ~> 4.0`, `azapi ~> 2.4`). The
`name_servers` output is what the handover lists for the delegation; `id` is what an alias record
in another zone, or a certificate issuer's role assignment, takes.

For a child zone (development, test) `ns_records` is empty and the production zone's variable
holds the children's name servers - read from the child stages' outputs after their first apply.

### Tests

`mock_provider "azurerm"`, `"azapi"`, `"modtm"` and `"random"`. The module wraps plain
`azurerm_dns_*` resources but exposes **no `resource` output**: `resource_id`, `name_servers` and
the per-type `*_record_outputs` are unknown at plan, so the plan shows the decisions only as the
module's internal resources, which an assert cannot address. The authored resources beside the
module are the root's own. Settled by a `terraform test` run on v0.2.1:

```hcl
run "dnssec" {
  command = plan

  assert {
    condition     = azapi_resource.dnssec.name == "default" && azapi_resource.dnssec.type == "Microsoft.Network/dnsZones/dnssecConfigs@2023-07-01-preview"
    error_message = "DNSSEC must be rendered as the zone's dnssecConfigs child."
  }
}

# not-testable: public-dns-zone.zone.zone_name - the module has no resource output; azurerm_dns_zone is inside it
# not-testable: public-dns-zone.zone.registrar_owner - an open entry in the handover, nothing in the plan
# not-testable: public-dns-zone.zone.child_zone_delegations - azurerm_dns_ns_record is inside the module
# not-testable: public-dns-zone.records.record_sets - as above, per type
# not-testable: public-dns-zone.records.verification_records - as above
# not-testable: public-dns-zone.records.record_ttl_seconds - as above
# not-testable: public-dns-zone.access.role_assignments - root resource with for_each over a variable; count is asserted where a pattern supplies entries
```

`terraform show -json` on the saved plan lists every `azurerm_dns_*_record` with its `records`;
a pipeline check over that file is where the record lists are verified.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the resource and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Resource |
|---|---|
| the zone | `azurerm_dns_zone` (`name`, `resource_group_name`; `soa_record` optional) - outputs `name_servers` |
| lock | `azurerm_management_lock` on the zone |

Validated against `azurerm` 5.x: on 5.x the public DNS records still take `zone_name` plus
`resource_group_name` (unlike the private zone's records, which moved to `private_dns_zone_id`).
