# Rendering a Virtual Machine as Terraform

Mapping from the question set to the machine. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-compute-virtualmachine/azurerm` | **v0.21.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.21.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm >= 3.116, < 5.0` -
**a root calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random`, `tls`,
and Terraform `>= 1.10`. The root's provider set is the union with the other modules. `zone` is
a **required** input: `null` for a region without zones.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call (Linux)

```hcl
module "vm" {
  source  = "Azure/avm-res-compute-virtualmachine/azurerm"
  version = "~> 0.21.0"
  # decision: virtual-machine.machine.instance_count - one call per machine; a single machine is a for_each of one
  for_each = toset([for i in range(var.instance_count) : tostring(i + 1)])

  name                = data.naming_name.vm[each.key].name
  location            = var.location
  resource_group_name = var.resource_group_name
  # decision: virtual-machine.machine.availability - one machine in a zone is placement, not redundancy
  zone = "1"

  # decision: virtual-machine.machine.os_type - the module's default is Windows
  os_type  = "Linux"
  sku_size = "Standard_D2ds_v5"
  source_image_reference = {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # decision: virtual-machine.machine.os_disk_storage
  os_disk = {
    caching                = "ReadWrite"
    storage_account_type   = "Premium_ZRS"
    disk_size_gb           = 64
    disk_encryption_set_id = var.disk_encryption_set_id # customer_managed only
  }

  network_interfaces = {
    primary = {
      name                           = "${data.naming_name.vm[each.key].name}-nic"
      accelerated_networking_enabled = true
      ip_configurations = {
        primary = {
          name                          = "ipconfig1"
          private_ip_subnet_resource_id = var.workload_subnet_id
          # decision: virtual-machine.networking.public_ip
          create_public_ip_address = false
        }
      }
    }
  }

  # decision: virtual-machine.security.password_authentication - key only, nothing generated into state
  account_credentials = {
    admin_credentials = {
      username                           = "azureuser"
      ssh_keys                           = [var.admin_ssh_public_key]
      generate_admin_password_or_ssh_key = false
    }
    password_authentication_disabled = true
  }

  # decision: virtual-machine.security.trusted_launch / encryption_at_host - the Bicep default is off
  secure_boot_enabled        = true
  vtpm_enabled               = true
  encryption_at_host_enabled = true
  patch_mode                 = "AutomaticByPlatform"
  patch_assessment_mode      = "AutomaticByPlatform"
  boot_diagnostics           = true

  managed_identities = { system_assigned = true }
  extensions = {
    entra_login = {
      name                       = "AADSSHLoginForLinux"
      publisher                  = "Microsoft.Azure.ActiveDirectory"
      type                       = "AADSSHLoginForLinux"
      type_handler_version       = "1.0"
      auto_upgrade_minor_version = true
    }
  }

  shutdown_schedules = {
    nightly = {
      daily_recurrence_time = "1900"
      timezone              = "UTC"
      enabled               = true
    }
  }

  azure_backup_configurations = {
    default = {
      recovery_vault_resource_id = var.backup_vault_id
      backup_policy_resource_id  = var.backup_policy_id
    }
  }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.vm.resource_id }
output "principal_id" { value = module.vm.system_assigned_mi_principal_id }
```

A Windows machine differs in `os_type = "Windows"`, the image (`MicrosoftWindowsServer` /
`WindowsServer` / `2022-datacenter-g2`), `os_disk.disk_size_gb = 128`, `license_type`, the
extension (`AADLoginForWindows`, handler `2.0`), and the credentials: no keys, and
`account_credentials.key_vault_configuration = { resource_id = var.credential_key_vault_id }`
with the generation flag left on. `shutdown_schedules` and `azure_backup_configurations` are
empty maps when the decisions are off. The Linux and Windows
calls were validated with `terraform validate` against v0.21.0 (azurerm 4.81, azapi 2.13).

The role assignments use the principal ids the pattern supplies; a role the machine's identity
needs elsewhere is `role_assignments_system_managed_identity` (external scopes) and is wiring.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the
image, the size, the zone, secure boot and vTPM, encryption at host, password authentication,
the patch mode and the OS disk type. The output paths are read off a first `terraform test` run
on the pinned version; the module builds a `azurerm_linux_virtual_machine` or
`azurerm_windows_virtual_machine` by `os_type`, and a test addresses the one that exists. What
the module builds in child resources - the extension, the shutdown schedule, the backup item,
the diagnostic setting - is marked `# not-testable:` with a reason where the plan hides it.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.
Linux and Windows are different resources.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
