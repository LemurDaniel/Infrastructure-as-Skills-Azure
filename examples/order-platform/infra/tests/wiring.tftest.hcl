# The root planned whole: what only the root can see, namely the resource groups and the wiring between the
# families. Each family's own decisions are asserted in modules/<family>/tests (terraform -chdir=modules/<family> test).
# Providers are mocked; the naming module is real.

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

mock_provider "azapi" {
  mock_data "azapi_resource" {
    defaults = {
      output = {
        properties = {
          frontDoorId = "11111111-1111-1111-1111-111111111111"
        }
      }
    }
  }
}

mock_provider "modtm" {}
mock_provider "random" {}
mock_provider "tls" {}
mock_provider "time" {}

variables {
  subscription_id          = "00000000-0000-0000-0000-000000000000"
  environment              = "development"
  location                 = "germanywestcentral"
  workload                 = "orders"
  tags                     = {}
  address_space            = "10.100.0.0/23"
  lock_enabled             = false
  publisher_name           = "OPEN-publisher-name"
  publisher_email          = "ops@example.com"
  function_runtime_name    = "node"
  function_runtime_version = "20"
  appgw_listener_hostnames = ["OPEN-appgw-listener-hostname"]
  vm_size                  = "OPEN-vm-size"
  vm_admin_ssh_public_key  = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILdvyP4lw/84PbXwja2S+uNDp+NzGXjgm9k1Nof7mQp7 test@example.com"
  event_function_name      = "OPEN-function-name"
}

run "resource_groups" {
  command = plan

  assert {
    condition     = jsonencode(sort(keys(module.resource_group))) == jsonencode(["application", "data", "main", "network", "observability"])
    error_message = "Five created groups: main plus network, data, application and observability."
  }

  assert {
    condition     = module.resource_group["main"].name == "rg-orders-dev" && module.resource_group["data"].name == "rg-orders-dev-data"
    error_message = "Group names come from Azure/naming/azurerm; the main group has no role part."
  }
}

run "wiring" {
  command = plan

  assert {
    condition     = jsonencode(sort(keys(azurerm_role_assignment.function))) == jsonencode(["host_blob", "host_queue", "sb_receive", "sb_send"])
    error_message = "The function app's identity gets its host storage roles and the Service Bus sender and receiver roles."
  }

  assert {
    condition     = azurerm_role_assignment.event_hubs_archive.role_definition_name == "Storage Blob Data Contributor"
    error_message = "The Event Hubs namespace writes its archive into the data lake with its own identity."
  }
}

run "production_stage" {
  command = plan

  variables {
    environment   = "production"
    address_space = "10.102.0.0/23"
    lock_enabled  = true
  }

  assert {
    condition     = module.resource_group["main"].name == "rg-orders-prd" && module.resource_group["observability"].name == "rg-orders-prd-observability"
    error_message = "The production stage carries its own stage code in every group name."
  }
}
