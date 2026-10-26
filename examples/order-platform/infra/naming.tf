# deployment.naming_source: module - Azure/naming/azurerm, no naming.yaml.
module "naming" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = local.naming_suffix
  unique-seed   = local.unique_seed
  unique-length = 4
}
