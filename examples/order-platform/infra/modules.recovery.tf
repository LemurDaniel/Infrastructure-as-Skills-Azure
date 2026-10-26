module "recovery" {
  source = "./modules/recovery"

  environment   = var.environment
  location      = var.location
  workload      = var.workload
  naming_suffix = local.naming_suffix
  unique_seed   = local.unique_seed
  tags          = var.tags

  resource_groups          = local.resource_groups
  lock_enabled             = var.lock_enabled
  diagnostic_workspace_id  = module.observability.workspace_id
  datalake_id              = module.data.datalake_id
  datalake_container_names = [module.data.datalake_telemetry_container]
  vm_ids                   = module.app.vm_ids
  vm_ready_ids             = module.app.vm_ready_ids
}
