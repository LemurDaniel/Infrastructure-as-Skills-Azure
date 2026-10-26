# Public IP of the Application Gateway. It sits in the main resource group (public IPs are not in the network role's table).
# decision: public-ip-address__appgw.address.purpose - application_gateway: Standard, static, regional.
module "public_ip_appgw" {
  source  = "Azure/avm-res-network-publicipaddress/azurerm"
  version = "~> 0.2.1"

  name                = module.naming_appgw.public_ip.name
  location            = var.location
  resource_group_name = var.resource_groups["main"].name

  sku               = "Standard"
  sku_tier          = "Regional"
  allocation_method = "Static"
  ip_version        = "IPv4"
  # application-gateway.networking.public_ip_zone_redundant follows zone_redundant: false - no zones.
  zones                   = []
  idle_timeout_in_minutes = 4
  domain_name_label       = null

  ddos_protection_mode = "VirtualNetworkInherited"

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
