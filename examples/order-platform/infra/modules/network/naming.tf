# deployment.naming_source: module - Azure/naming/azurerm. One call per instance that needs its own suffix.
module "naming" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_appgw" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = concat(var.naming_suffix, ["appgw"])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_nsg" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(["appgw", "apim", "workload", "pe"])

  suffix        = concat(var.naming_suffix, [each.key])
  unique-seed   = var.unique_seed
  unique-length = 4
}
