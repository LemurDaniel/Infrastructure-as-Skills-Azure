module "app" {
  source = "./modules/app"

  environment   = var.environment
  location      = var.location
  workload      = var.workload
  naming_suffix = local.naming_suffix
  unique_seed   = local.unique_seed
  tags          = var.tags

  resource_groups             = local.resource_groups
  apim_name                   = local.apim_name
  subnet_ids                  = module.network.subnet_ids
  private_dns_zone_ids        = module.network.private_dns_zone_ids
  diagnostic_workspace_id     = module.observability.workspace_id
  function_identity_id        = module.security.identity_ids["function"]
  function_identity_client_id = module.security.identity_client_ids["function"]
  host_storage_name           = module.data.host_storage_name
  host_storage_blob_endpoint  = module.data.host_storage_blob_endpoint
  host_deployment_container   = module.data.host_deployment_container
  publisher_name              = var.publisher_name
  publisher_email             = var.publisher_email
  function_runtime_name       = var.function_runtime_name
  function_runtime_version    = var.function_runtime_version
  vm_size                     = var.vm_size
  vm_admin_ssh_public_key     = var.vm_admin_ssh_public_key
}
