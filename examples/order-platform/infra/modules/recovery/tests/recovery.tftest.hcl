# Recovery family, planned alone: `terraform -chdir=modules/recovery test`.

mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000000"
      tenant_id       = "00000000-0000-0000-0000-000000000000"
      object_id       = "00000000-0000-0000-0000-000000000000"
      client_id       = "00000000-0000-0000-0000-000000000000"
    }
  }
}
mock_provider "azapi" {}
mock_provider "modtm" {}
mock_provider "random" {}
mock_provider "time" {}

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  lock_enabled  = false
  resource_groups = {
    data = {
      name = "rg-orders-dev-data"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-data"
    }
  }
  diagnostic_workspace_id  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-observability/providers/Microsoft.OperationalInsights/workspaces/log-orders-dev"
  datalake_id              = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-data/providers/Microsoft.Storage/storageAccounts/stordersdevdla1b2"
  datalake_container_names = ["telemetry"]
  vm_ready_ids = {
    "1" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-1"
    "2" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-2"
    "3" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-3"
  }
  vm_ids = {
    "1" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-1"
    "2" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-2"
    "3" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Compute/virtualMachines/vm-orders-dev-3"
  }
}

run "naming" {
  command = plan

  assert {
    condition     = module.backup_vault.backup_vault_name == "bvault-orders-dev" && module.recovery_vault.resource.name == "rsv-orders-dev"
    error_message = "Names come from Azure/naming/azurerm: <slug>-<workload>-<stage>."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
  }

  assert {
    condition     = module.backup_vault.backup_vault_name == "bvault-orders-tst"
    error_message = "The test stage carries its own stage code."
  }
}

run "backup_vault" {
  command = plan

  # decision: backup-vault.protection.protected_resources
  assert {
    condition     = jsonencode(keys(module.backup_vault.backup_instance_ids)) == jsonencode(["datalake"])
    error_message = "The data lake is the one protected resource."
  }

  # not-testable: backup-vault.vault.immutability - the module outputs no vault attributes; the vault is an azapi resource inside it
  # decision: backup-vault.vault.multi_user_authorization
  assert {
    condition     = module.backup_vault.resource_guard_id == null
    error_message = "No resource guard: multi-user authorization is off."
  }
}

run "recovery_services_vault" {
  command = plan

  # decision: recovery-services-vault.protection.protected_resources
  # decision: virtual-machine.data_protection.backup_enabled
  # The two decisions are one fact: every virtual machine is protected by this vault. Asserted once, under the
  # vault, because a decision is asserted by exactly one test.
  assert {
    condition     = jsonencode(sort(keys(module.recovery_vault.backup_protected_vm))) == jsonencode(["vm-1", "vm-2", "vm-3"])
    error_message = "Every virtual machine is protected, although the derived value would have been no backup."
  }

  # decision: recovery-services-vault.vault.soft_delete
  assert {
    condition     = module.recovery_vault.resource.body.properties.securitySettings.softDeleteSettings.softDeleteState == "Enabled"
    error_message = "Soft delete is on."
  }
}
