data "azurerm_client_config" "current" {}

locals {
  # decision: virtual-machine.instances - 3, assumed ("a few VMs")
  vm_instances = 3
  vm_keys      = [for i in range(local.vm_instances) : tostring(i + 1)]
}

module "naming_vm" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(local.vm_keys)

  suffix        = concat(var.naming_suffix, [each.key])
  unique-seed   = var.unique_seed
  unique-length = 4
}

# The machines sit in the main resource group (virtual machines are not in the table of a split role).
module "virtual_machine" {
  source  = "Azure/avm-res-compute-virtualmachine/azurerm"
  version = "~> 0.21.0"

  for_each = toset(local.vm_keys)

  name                = module.naming_vm[each.key].linux_virtual_machine.name
  location            = var.location
  resource_group_name = var.resource_groups["main"].name
  # Not zonal: outage_impact tolerable, nothing in the spec asks for a zone.
  zone = null

  # decision: virtual-machine.machine.os_type - the module default is Windows
  os_type = "Linux"
  # OPEN (size and purpose of the VMs)
  sku_size = var.vm_size
  source_image_reference = {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  os_disk = {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  network_interfaces = {
    primary = {
      name                           = "${module.naming_vm[each.key].linux_virtual_machine.name}-nic"
      accelerated_networking_enabled = true
      ip_configurations = {
        primary = {
          name                          = "ipconfig1"
          private_ip_subnet_resource_id = var.subnet_ids["workload"]
          create_public_ip_address      = false
        }
      }
    }
  }

  # Key only; OPEN (ssh public key). Nothing generated into state.
  account_credentials = {
    admin_credentials = {
      username                           = "azureuser"
      ssh_keys                           = [var.vm_admin_ssh_public_key]
      generate_admin_password_or_ssh_key = false
    }
    password_authentication_disabled = true
  }

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

  # decision: virtual-machine.data_protection.backup_enabled
  # OVERRIDE (derived: false): the customer asked for VM backup. The protection item is created by the
  # Recovery Services vault in the recovery family (backup_protected_vm), because the vault needs these VMs.

  diagnostic_settings = {
    workspace = {
      # The module requires a name here (it has no default).
      name                  = "diag-${module.naming_vm[each.key].linux_virtual_machine.name}"
      workspace_resource_id = var.diagnostic_workspace_id
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
