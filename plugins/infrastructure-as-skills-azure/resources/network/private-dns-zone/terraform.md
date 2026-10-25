# Rendering a private DNS zone as Terraform

Mapping from the question set to the private DNS zone. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-privatednszone/azurerm` | **v0.5.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.5.0`.

**AzAPI only**: it takes `parent_id` and requires `azapi ~> 2.4`, `modtm ~> 0.3`,
`random >= 3.5.1, < 5.0`, `time ~> 0.13`, Terraform `>= 1.9`; no `azurerm`. The root's provider
set is the union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `zone_names` | `domain_name` | One module call per zone, `for_each` over the names so the address is the zone: `module.private_dns_zone["privatelink.blob.core.windows.net"]` |
| `vnet_links` | `virtual_network_links = { <k> = { name, virtual_network_id, registration_enabled, resolution_policy } }` | A map keyed by the network's role; the module also takes the older `vnetlinkname` / `vnetid` / `autoregistration` spellings - not used |
| `auto_registration` | `virtual_network_links.<k>.registration_enabled` | `false` unless `zone_kind: internal_domain` says otherwise |
| `resolution_policy` | `virtual_network_links.<k>.resolution_policy` | `"Default"` or `"NxDomainRedirect"` |
| `static_records` | `a_records`, `aaaa_records`, `cname_records`, `txt_records` ... | A map per type; `a_records = { <k> = { name, ttl, records = [...] } }` |
| `resource_group_name` | `parent_id` | The resource group's id (the module also accepts a virtual network's) |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.5.0: nothing from this question set. `soa_record`,
`mx_records`, `srv_records`, `ptr_records` and `role_assignments` are inputs the question set has
no decision for - leave them unset rather than inventing a default.

### The call

```hcl
module "private_dns_zone" {
  for_each = toset(["privatelink.vaultcore.azure.net"]) # private-dns-zone.zone.zone_names

  source  = "Azure/avm-res-network-privatednszone/azurerm"
  version = "~> 0.5.0"

  domain_name = each.key
  parent_id   = data.azurerm_resource_group.this.id

  # decision: private-dns-zone.networking.vnet_links
  virtual_network_links = {
    for k, id in var.virtual_network_ids : k => {
      name               = "pdnsz-${k}"
      virtual_network_id = id
      # decision: private-dns-zone.networking.auto_registration
      registration_enabled = false
      # decision: private-dns-zone.networking.resolution_policy
      resolution_policy = "Default"
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "ids" {
  value = { for k, z in module.private_dns_zone : k => z.resource_id }
}
```

For `zone_kind: internal_domain`, `static_records` becomes the record maps, for example
`a_records = { app = { name = "app", ttl = 300, records = ["10.0.0.4"] } }`, and
`registration_enabled` follows `auto_registration`. Validated with `terraform validate`
(registry, v0.5.0) in a root together with the other four modules of this family, and the
record map with a plan.

The ids go to the private-endpoint renders (`private_dns_zone_resource_ids`) and to the
resources' own `private_endpoints` inputs, by zone name.

### Tests

`mock_provider "azapi"`, `"modtm"` and `"random"`. The module's `name` and `resource_id` outputs
and the link and record outputs are **unknown at plan**, and its `resource` output is the zone
before apply - so a plan shows the decisions only as the `azapi_resource` bodies, which
`terraform test` cannot read, and each decision is marked `# not-testable:` with that reason.
Settled by a `terraform test` run on v0.5.0:

```hcl
# not-testable: private-dns-zone.zone.ownership - inherited; decides whether this module is called, which the root's wiring test sees
# not-testable: private-dns-zone.zone.zone_kind - decides which questions are reached; nothing of its own in the plan
# not-testable: private-dns-zone.zone.zone_names - the zone name is unknown at plan (module name output); read from the plan JSON
# not-testable: private-dns-zone.networking.vnet_links - the links are module-internal azapi resources; their count is in the plan JSON
# not-testable: private-dns-zone.networking.auto_registration - inside the link body
# not-testable: private-dns-zone.networking.resolution_policy - inside the link body; the module sends null for "Default"
# not-testable: private-dns-zone.records.static_records - the record outputs are unknown at plan
```

`terraform show -json` on the saved plan shows `Microsoft.Network/privateDnsZones@2024-06-01`,
the `.../virtualNetworkLinks` children and the `.../A` records with their bodies; a pipeline check
over that file is the place for these.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource |
|---|---|
| the zone | `azurerm_private_dns_zone` (`name`, `resource_group_name`) |
| `vnet_links` | `azurerm_private_dns_zone_virtual_network_link` - **`private_dns_zone_id`** and `virtual_network_id`; on 5.x there is no `resource_group_name` or `private_dns_zone_name` |
| `auto_registration` | `registration_enabled` |
| `resolution_policy` | `resolution_policy` |
| `static_records` | `azurerm_private_dns_a_record`, `_cname_record`, `_txt_record` - **`private_dns_zone_id`** on 5.x, not `zone_name` and `resource_group_name` |

Validated against `azurerm` 5.x. The 4.x spelling (zone name plus resource group on links and
records) is rejected by 5.x.
