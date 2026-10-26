# Observability family, planned alone: `terraform -chdir=modules/observability test`.

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
  lock_enabled  = false
  resource_groups = {
    observability = {
      name = "rg-orders-dev-observability"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-observability"
    }
  }
}

run "naming" {
  command = plan

  assert {
    condition     = module.workspace.resource.name == "log-orders-dev"
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
    condition     = module.workspace.resource.name == "log-orders-tst"
    error_message = "The test stage carries its own stage code."
  }
}

run "cost" {
  command = plan

  # decision: log-analytics-workspace.cost.retention_days
  assert {
    condition     = module.workspace.resource.retention_in_days == 30
    error_message = "Retention as stated in the deployment set: 30 days."
  }
}
