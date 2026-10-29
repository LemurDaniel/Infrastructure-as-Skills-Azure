# deployment.private_dns_ownership: deployment - the zones are created here and linked to the stage's network;
# the private endpoints of the other families attach them through their zone groups.
# The zones sit in the main resource group (they are not in the network role's table).
module "private_dns_zone" {
  source  = "Azure/avm-res-network-privatednszone/azurerm"
  version = "~> 0.5.0"

  # decision: private-dns-zone.zone.zone_names
  for_each = toset(local.private_dns_zones)

  domain_name = each.key
  parent_id   = var.resource_groups["main"].id

  virtual_network_links = {
    vnet = {
      name                 = "link-${module.naming.virtual_network.name}"
      virtual_network_id   = module.virtual_network.resource_id
      registration_enabled = false
      resolution_policy    = "Default"
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
