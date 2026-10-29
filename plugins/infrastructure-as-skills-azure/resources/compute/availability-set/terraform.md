# Rendering an Availability Set as Terraform

Mapping from the question set to the set and its optional proximity placement group. General
layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Resource | Module | Documented against | Resolved | Status |
|---|---|---|---|---|
| Availability set | none - **`avm-res-compute-availabilityset` is not published** | - | 2026-10-25 | Not in the registry: render the authored resource below, `implementation: authored`, `source: { forced_by: no AVM module for Microsoft.Compute/availabilitySets }` |
| Proximity placement group | `Azure/avm-res-compute-proximityplacementgroup/azurerm` | **0.1.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The PPG module is pinned exactly
(`0.1.0`): at `0.x` with a single release a `~>` pin has no minor to follow.

The PPG module is **`azurerm`-based** with `resource_group_name`, and requires `azurerm >= 3.116.0, < 5.0.0` -
**a root calling it cannot be on 5.x** - plus `modtm` pinned to exactly `0.3.2`, `random`, and
Terraform `~> 1.9`. In a root on `azurerm` 5.x use the authored group below.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `proximity_placement_group` | the module call itself | Rendered only when `true` |
| `proximity_zone` | `zone` | Module default **`"1"`**; `none` is `null`; written |
| `proximity_vm_sizes` | `allowed_vm_sizes` | `null` when empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
# decision: availability-set.proximity.proximity_placement_group - rendered only when true
module "proximity_placement_group" {
  source  = "Azure/avm-res-compute-proximityplacementgroup/azurerm"
  version = "0.1.0"

  name                = data.naming_name.proximity_placement_group.name # "Azure::Microsoft.Compute/proximityPlacementGroups"
  location            = var.location
  resource_group_name = var.resource_group_name
  # decision: availability-set.proximity.proximity_zone - the module's default is "1"; a set's machines have no zone
  zone             = null
  allowed_vm_sizes = ["Standard_D2ds_v5"]
  enable_telemetry = true
  tags             = local.tags
}

resource "azurerm_availability_set" "this" {
  name                = data.naming_name.availability_set.name # "Azure::Microsoft.Compute/availabilitySets"
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: availability-set.set.sku
  managed = true
  # decision: availability-set.set.fault_domain_count - the provider's default is 3, which fails in a two-domain region
  platform_fault_domain_count = 2
  platform_update_domain_count = 5

  proximity_placement_group_id = module.proximity_placement_group.resource_id # null when no group
  tags                         = local.tags
}

output "id" { value = azurerm_availability_set.this.id }
```

The two blocks, with the module under `azurerm` 4.81, were validated with `terraform validate`.
Whether the module accepts `zone = null` at plan time against a real subscription is not
verified: the variable is documented as required and the validation only checks the shape.

### Tests

With `azurerm` mocked, asserts target the availability set resource: the domain counts, the
`managed` flag and the group reference. The module's group is asserted through its
`resource` output; the zone and the allowed sizes are marked `# not-testable:` with a reason
where the module hides them in a child resource.

## Authored rendering

The only form of the availability set, and the fallback for the group. Targets `azurerm`
**5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_availability_set` / `azurerm_proximity_placement_group` |
|---|---|
| `sku` | `managed` (`true` is `Aligned`) |
| `fault_domain_count`, `update_domain_count` | `platform_fault_domain_count`, `platform_update_domain_count` |
| `proximity_placement_group` | `azurerm_proximity_placement_group` and `proximity_placement_group_id` on the set |
| `proximity_zone` | `zone` on the group (omitted for `none`) |
| `proximity_vm_sizes` | `allowed_vm_sizes` |

```hcl
resource "azurerm_proximity_placement_group" "this" {
  name                = data.naming_name.proximity_placement_group.name
  location            = var.location
  resource_group_name = var.resource_group_name
  allowed_vm_sizes    = ["Standard_D2ds_v5"]
  tags                = local.tags
}

resource "azurerm_availability_set" "this" {
  name                         = data.naming_name.availability_set.name
  location                     = var.location
  resource_group_name          = var.resource_group_name
  managed                      = true
  platform_fault_domain_count  = 2
  platform_update_domain_count = 5
  proximity_placement_group_id = azurerm_proximity_placement_group.this.id
  tags                         = local.tags
}
```

Validated with `terraform validate` against `azurerm` 5.11.
