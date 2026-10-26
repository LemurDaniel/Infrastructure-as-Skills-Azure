# Security family, planned alone: `terraform -chdir=modules/security test`.
# user-assigned-identity__function and __appgw carry no decisions in the spec (their question set has none that
# applies), so there is nothing to mark here; the test checks the names and the purpose tag.

mock_provider "azurerm" {}
mock_provider "azapi" {}
mock_provider "modtm" {}
mock_provider "random" {}

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  resource_groups = {
    main = {
      name = "rg-orders-dev"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev"
    }
  }
}

run "naming" {
  command = plan

  assert {
    condition     = module.identity["function"].resource_name == "uai-orders-dev-function" && module.identity["appgw"].resource_name == "uai-orders-dev-appgw"
    error_message = "Names come from Azure/naming/azurerm: <slug>-<workload>-<stage>-<purpose>."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
  }

  assert {
    condition     = module.identity["function"].resource_name == "uai-orders-tst-function"
    error_message = "The test stage carries its own stage code."
  }
}
