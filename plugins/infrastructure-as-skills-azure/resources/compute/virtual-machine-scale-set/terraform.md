# Rendering a Virtual Machine Scale Set as Terraform

Mapping from the question set to the scale set. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-compute-virtualmachinescaleset/azurerm` | **v0.11.1** | 2026-10-25 | Available - **Flexible orchestration only** |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.11.0`.

**AzAPI-based**: it takes `parent_id` (the **id** of the resource group) and requires
`azapi ~> 2.12`, `modtm ~> 0.3`, `random >= 3.6.2` and Terraform `>= 1.9`; it constrains no
`azurerm`, so the root can be on 5.x. Two required inputs are **ephemeral**:
`extension_protected_setting` (`{}` unused) and `user_data_base64` (`null` unused).

Named gaps: no input for trusted launch (secure boot, vTPM) and none for a diagnostic setting;
a Uniform set is not rendered at all. Both gaps are said in the handover; the diagnostic setting
is a sibling `azurerm_monitor_diagnostic_setting`, unverified for this resource type.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call (Linux)

```hcl
module "vmss" {
  source  = "Azure/avm-res-compute-virtualmachinescaleset/azurerm"
  version = "~> 0.11.0"

  name      = data.naming_name.vmss.name
  location  = var.location
  parent_id = var.resource_group_id # the resource group's id, not its name

  # decision: virtual-machine-scale-set.scale_set.orchestration_mode - the module renders Flexible only
  sku_name  = "Standard_D2ds_v5"
  instances = 2
  # decision: virtual-machine-scale-set.scale_set.zones
  zones                       = ["1", "2", "3"]
  zone_balance                = false
  platform_fault_domain_count = 1
  single_placement_group      = false

  source_image_reference = {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # decision: virtual-machine-scale-set.security.password_authentication
  os_profile = {
    linux_configuration = {
      admin_username                  = "azureuser"
      disable_password_authentication = true
      patch_mode                      = "AutomaticByPlatform"
      patch_assessment_mode           = "AutomaticByPlatform"
      admin_ssh_key_id                = ["azureuser"]
    }
  }
  admin_ssh_keys = [{
    id         = "azureuser"
    public_key = var.admin_ssh_public_key
    username   = "azureuser"
  }]

  os_disk = {
    caching                = "ReadWrite"
    storage_account_type   = "Premium_LRS"
    disk_size_gb           = 64
    disk_encryption_set_id = var.disk_encryption_set_id # customer_managed only
  }

  network_interface = [{
    name                          = "nic"
    primary                       = true
    enable_accelerated_networking = true
    ip_configuration = [{
      name                                   = "ipconfig1"
      primary                                = true
      subnet_id                              = var.workload_subnet_id
      load_balancer_backend_address_pool_ids = var.load_balancer_backend_pool_ids
      # decision: virtual-machine-scale-set.networking.public_ip - no public_ip_address block
    }]
  }]

  # decision: virtual-machine-scale-set.security.encryption_at_host - the Bicep module's default is on
  encryption_at_host_enabled = true

  # decision: virtual-machine-scale-set.scale_set.instance_repair - needs the health extension below
  automatic_instance_repair = { enabled = true, grace_period = "PT30M" }
  upgrade_policy            = { upgrade_mode = "Manual" }
  extension = [{
    name                               = "ApplicationHealthLinux"
    publisher                          = "Microsoft.ManagedServices"
    type                               = "ApplicationHealthLinux"
    type_handler_version               = "1.0"
    auto_upgrade_minor_version_enabled = true
    settings = jsonencode({
      protocol    = "http"
      port        = var.health_check_port
      requestPath = "/"
    })
  }]
  extension_protected_setting = {}
  user_data_base64            = null

  boot_diagnostics   = {}
  managed_identities = { user_assigned_resource_ids = [var.user_assigned_identity_id] }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.vmss.resource_id }
```

A Windows set differs in `os_profile.windows_configuration` (`admin_username`,
`patch_mode`), `admin_password`, the
image, `os_disk.disk_size_gb = 128` and the extension (`ApplicationHealthWindows`). The Linux
call was validated with `terraform validate` against v0.11.1 (azapi 2.13); `terraform plan`
runs the module's preconditions on repair and rolling upgrades and was not run against a
subscription. `port` is the `health_check_port` answer (80 in the validated file).

### Tests

With `azapi` mocked, asserts target what the plan shows of the module's `azapi_resource`: the
SKU name and capacity, the zones, the upgrade policy, the repair policy and the profile body.
The body is JSON in `azapi_resource`, so the asserts address its keys, read off a first
`terraform test` run on the pinned version. What the module builds in child resources - the
extensions, the role assignments - is marked `# not-testable:` with a reason where the plan
hides it.

## Authored rendering

The fallback, and the only form of a Uniform set. Targets `azurerm` **5.x**; check against
`terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Flexible and Uniform authored resources were validated with `terraform validate` against
`azurerm` 5.11.
