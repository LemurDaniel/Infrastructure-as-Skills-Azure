# Rendering a maintenance configuration as Terraform

Mapping from the question set to the maintenance configuration. General layout, variables and
tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-maintenance-maintenanceconfiguration/azurerm` | **v0.2.0** | 2026-11-01 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**AzAPI only**: the configuration is an `azapi_resource` and takes the resource group as
`parent_id` (an id). Requires `azapi ~> 2.12`, `time ~> 0.13`, Terraform `>= 1.9, < 2.0`; no
`azurerm`, so the root stays on `azurerm` 5.x. The root's provider set is the union with the
other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| (the configuration) | `name` through the naming provider | `subname` carries the window's role: `mc-gwc-dev-telemetry-patch-01` |
| (scope `InGuestPatch`) | `extension_properties = { InGuestPatchMode = "User" }` | Written with the scope, never asked |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.2.0: the assignment - it is the machine's
(`maintenance_configuration_resource_ids` on the virtual-machine module). `window.expiration_date_time`,
`role_assignments` and `lock` are inputs the question set has no decision for - leave them
unset (`lock`: `deployment.resource_lock` does not list this resource).

### The call

```hcl
data "naming_name" "maintenance_configuration" {
  resource   = "Azure::Microsoft.Maintenance/maintenanceConfigurations"
  parameters = { subname = "patch" }
}

module "maintenance_configuration" {
  source  = "Azure/avm-res-maintenance-maintenanceconfiguration/azurerm"
  version = "~> 0.2.0"

  name      = data.naming_name.maintenance_configuration.name
  location  = var.location
  parent_id = var.resource_group_id

  # decision: maintenance-configuration.schedule.scope
  scope                = "InGuestPatch"
  extension_properties = { InGuestPatchMode = "User" }
  # decision: maintenance-configuration.patches.visibility
  visibility = "Custom"

  window = {
    # decision: maintenance-configuration.schedule.start_date + schedule.start_time - per stage
    start_date_time = "${var.maintenance_start_date} ${var.maintenance_start_time}"
    duration        = "03:00"                  # decision: maintenance-configuration.schedule.duration
    time_zone       = "UTC"                    # decision: maintenance-configuration.schedule.time_zone
    recur_every     = var.maintenance_recur_every # decision: maintenance-configuration.schedule.recur_every - per stage
  }

  install_patches = {
    reboot_setting = "IfRequired" # decision: maintenance-configuration.patches.reboot_setting
    # decision: maintenance-configuration.patches.operating_systems - one object per listed system
    linux = {
      classifications_to_include    = ["Critical", "Security"]
      package_name_masks_to_exclude = []
      package_name_masks_to_include = []
    }
    windows = {
      classifications_to_include   = ["Critical", "Security"]
      kb_numbers_to_exclude        = []
      kb_numbers_to_include        = []
      exclude_kbs_requiring_reboot = false
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.maintenance_configuration.resource_id }
```

The machine takes the output:

```hcl
module "virtual_machine" {
  # ...
  patch_mode                                             = "AutomaticByPlatform"
  bypass_platform_safety_checks_on_user_schedule_enabled = true
  maintenance_configuration_resource_ids                 = { patch = module.maintenance_configuration.resource_id }
}
```

Validated with `terraform validate` (registry, v0.2.0, `azapi ~> 2.12`) in a root beside
`azurerm` 5.12.

### Tests

`mock_provider "azapi"` and `"time"`; the naming provider stays real. The module exports only
`resource_id` and `name`, and the configuration is an `azapi_resource` whose body is not an
output, so the decisions are read from the plan JSON rather than asserted:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.maintenance_configuration.name == "mc-gwc-dev-telemetry-patch-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

# not-testable: maintenance-configuration.schedule.scope - inside the module's azapi body; read from the plan JSON
# not-testable: maintenance-configuration.schedule.recur_every - as above
# not-testable: maintenance-configuration.schedule.start_date - as above
# not-testable: maintenance-configuration.schedule.start_time - as above
# not-testable: maintenance-configuration.schedule.duration - as above
# not-testable: maintenance-configuration.schedule.time_zone - as above
# not-testable: maintenance-configuration.patches.reboot_setting - as above
# not-testable: maintenance-configuration.patches.operating_systems - as above
# not-testable: maintenance-configuration.patches.linux_classifications - as above
# not-testable: maintenance-configuration.patches.linux_packages_to_exclude - as above
# not-testable: maintenance-configuration.patches.linux_packages_to_include - as above
# not-testable: maintenance-configuration.patches.windows_classifications - as above
# not-testable: maintenance-configuration.patches.windows_kbs_to_exclude - as above
# not-testable: maintenance-configuration.patches.windows_kbs_to_include - as above
# not-testable: maintenance-configuration.patches.windows_exclude_kbs_requiring_reboot - as above
# not-testable: maintenance-configuration.patches.visibility - as above
```

The assignment is asserted in the virtual-machine run: the machine module's input holds the
configuration's id.

## Authored rendering

The fallback. Targets `azurerm` **5.x**: `azurerm_maintenance_configuration` with `scope`,
`visibility`, `in_guest_user_patch_mode = "User"`, a `window` block (`start_date_time`,
`duration`, `time_zone`, `recur_every`) and an `install_patches` block (`reboot`, `linux`,
`windows`). The spellings differ from the module: `reboot`, not `reboot_setting`;
`package_names_mask_to_*`, not `package_name_masks_to_*`. There is no
`exclude_kbs_requiring_reboot` argument - `true` renders the configuration as an
`azapi_resource` of `Microsoft.Maintenance/maintenanceConfigurations@2023-04-01`. The assignment
is `azurerm_maintenance_assignment_virtual_machine` (or `_virtual_machine_scale_set`). Check
against `terraform providers schema -json`.

What each decision renders to - the resource and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Validated against `azurerm` 5.12.
