module "naming" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

# Backup vault (Data Protection) for the data lake's blobs. Both vaults sit in the data resource group.
module "backup_vault" {
  source  = "Azure/avm-res-dataprotection-backupvault/azurerm"
  version = "~> 2.0.9"

  name                = module.naming.data_protection_backup_vault.name
  location            = var.location
  resource_group_name = var.resource_groups["data"].name

  # Changing the redundancy forces a new vault. Reproducible data, tolerable outage: locally redundant.
  redundancy     = "LocallyRedundant"
  datastore_type = "VaultStore"

  cross_region_restore_enabled = false
  # decision: backup-vault.vault.immutability
  immutability = "Disabled"
  # Soft delete is always on in the current API version; the module has no switch. 14 days is the minimum.
  retention_duration_in_days = 14
  # decision: backup-vault.vault.multi_user_authorization - false: no resource guard
  resource_guard_enabled      = false
  alerts_for_all_job_failures = "Enabled"

  managed_identities = {
    system_assigned = true
  }

  # The vault's identity reads the storage account it protects; granted in the same apply as the backup
  # instance, which the module does not order - a first apply can fail on role propagation and passes on the second.
  role_assignments = {
    datalake_backup = {
      role_definition_id_or_name = "Storage Account Backup Contributor"
      principal_id               = "system-assigned"
      scope                      = var.datalake_id
      principal_type             = "ServicePrincipal"
    }
  }

  backup_policies = {
    blob = {
      type                             = "blob"
      name                             = "blob-daily"
      backup_repeating_time_intervals  = ["R/2026-01-01T02:00:00+00:00/P1D"]
      vault_default_retention_duration = "P30D"
    }
  }

  # decision: backup-vault.protection.protected_resources - storage-account__datalake
  backup_instances = {
    datalake = {
      type                            = "blob"
      name                            = "datalake"
      backup_policy_key               = "blob"
      storage_account_id              = var.datalake_id
      storage_account_container_names = var.datalake_container_names
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupProtectedInstance"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  # deployment.resource_lock: production
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
