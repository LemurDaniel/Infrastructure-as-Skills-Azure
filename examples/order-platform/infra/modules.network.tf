module "network" {
  source = "./modules/network"

  environment   = var.environment
  location      = var.location
  workload      = var.workload
  naming_suffix = local.naming_suffix
  unique_seed   = local.unique_seed
  tags          = var.tags

  resource_groups          = local.resource_groups
  address_space            = var.address_space
  appgw_identity_id        = module.security.identity_ids["appgw"]
  appgw_backend_hostname   = "${local.apim_name}.azure-api.net"
  appgw_listener_hostnames = var.appgw_listener_hostnames
}
