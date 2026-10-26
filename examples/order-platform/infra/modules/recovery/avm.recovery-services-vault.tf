# The protection items need the machines to exist. vm_ids are plan-time strings (the module's for_each cannot take
# apply-time values), so the order comes from this resource instead, which waits for the machines as created.
resource "terraform_data" "vms_ready" {
  input = var.vm_ready_ids
}

# Recovery Services vault for the virtual machines.
module "recovery_vault" {
  source  = "Azure/avm-res-recoveryservices-vault/azurerm"
  version = "~> 1.3.3"

  name                = module.naming.recovery_services_vault.name
  location            = var.location
  resource_group_name = var.resource_groups["data"].name

  sku = "Standard"
  # Reproducible data, tolerable outage: locally redundant. The module default is GeoRedundant.
  storage_mode_type = "LocallyRedundant"
  # Cross-region restore needs geo redundancy; the module default is true.
  cross_region_restore_enabled = false
  # decision: recovery-services-vault.vault.soft_delete
  soft_delete_enabled = "Enabled"
  immutability        = "Disabled"
  # No resource guard (multi-user authorization is not decided for this vault).
  resource_guard_association_enabled  = false
  alerts_for_all_job_failures_enabled = true

  managed_identities = {
    system_assigned = true
  }

  # Public access stays on: the spec lists no private endpoint and none of the backup DNS zones
  # (privatelink.<region>.backup.windowsazure.com) for this vault, and VM backup needs one of the two paths.
  # The module default is true as well.
  public_network_access_enabled = true

  vm_backup_policy = {
    daily = {
      name        = "vm-daily"
      timezone    = "UTC"
      policy_type = "V2"
      frequency   = "Daily"
      backup = {
        time = "23:00"
      }
      instant_restore_retention_days = 2
      retention_daily                = 14
    }
  }

  # decision: recovery-services-vault.protection.protected_resources - virtual-machine
  # decision: virtual-machine.data_protection.backup_enabled
  # OVERRIDE (derived: false, "reproducible"): the customer asked for VM backup; every VM is protected here.
  backup_protected_vm = {
    for k, id in var.vm_ids : "vm-${k}" => {
      source_vm_id          = id
      vm_backup_policy_name = "daily"
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupAlerts", "AddonAzureBackupProtectedInstance"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  # deployment.resource_lock: production
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags

  depends_on = [terraform_data.vms_ready]
}
