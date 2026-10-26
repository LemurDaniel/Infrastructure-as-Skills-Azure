module "observability" {
  source = "./modules/observability"

  environment   = var.environment
  location      = var.location
  workload      = var.workload
  naming_suffix = local.naming_suffix
  unique_seed   = local.unique_seed
  tags          = var.tags

  resource_groups = local.resource_groups
  lock_enabled    = var.lock_enabled
}
