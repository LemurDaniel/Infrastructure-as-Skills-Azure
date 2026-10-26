module "messaging" {
  source = "./modules/messaging"

  environment   = var.environment
  location      = var.location
  workload      = var.workload
  naming_suffix = local.naming_suffix
  unique_seed   = local.unique_seed
  tags          = var.tags

  resource_groups              = local.resource_groups
  lock_enabled                 = var.lock_enabled
  private_endpoint_subnet_id   = module.network.subnet_ids["private-endpoints"]
  private_dns_zone_ids         = module.network.private_dns_zone_ids
  diagnostic_workspace_id      = module.observability.workspace_id
  datalake_id                  = module.data.datalake_id
  datalake_telemetry_container = module.data.datalake_telemetry_container
  function_app_id              = module.app.function_app_id
  event_function_name          = var.event_function_name
}
