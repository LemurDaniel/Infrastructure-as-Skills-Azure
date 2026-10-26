locals {
  # Short stage code for the names (Azure/naming has no environment mapping of its own).
  environment_codes = {
    development = "dev"
    test        = "tst"
    production  = "prd"
  }

  # Suffix of every name: <slug>-<workload>-<stage>[-<role>] (Azure/naming/azurerm).
  naming_suffix = [var.workload, local.environment_codes[var.environment]]

  # Global names carry a 4-character suffix; derived from the scope so that a name is stable
  # across plans and the same in every module that needs it.
  unique_seed = substr(sha256("${var.subscription_id}/${var.workload}/${var.environment}"), 0, 8)

  resource_group_roles = ["main", "network", "data", "application", "observability"]

  # Resolved in the root because two families need it: the network family (Application Gateway
  # backend pool) and the app family (the service itself).
  apim_name = module.naming.api_management.name_unique
}
