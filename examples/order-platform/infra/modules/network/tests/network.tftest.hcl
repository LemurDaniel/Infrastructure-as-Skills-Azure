# Network family, planned alone: `terraform -chdir=modules/network test`.
# Providers are mocked, the naming module is real, so names are asserted as they will be deployed.
# The AVM modules' own tests cover their mapping; what is asserted here is that this family passes these decisions.

mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000000"
      tenant_id       = "00000000-0000-0000-0000-000000000000"
      object_id       = "00000000-0000-0000-0000-000000000000"
      client_id       = "00000000-0000-0000-0000-000000000000"
    }
  }
}

mock_provider "azapi" {
  mock_data "azapi_resource" {
    defaults = {
      output = {
        properties = {
          frontDoorId = "11111111-1111-1111-1111-111111111111"
        }
      }
    }
  }
}

mock_provider "modtm" {}
mock_provider "random" {}

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  resource_groups = {
    main = {
      name = "rg-orders-dev"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev"
    }
    network = {
      name = "rg-orders-dev-network"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network"
    }
  }
  address_space            = "10.100.0.0/23"
  appgw_identity_id        = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uai-orders-dev-appgw"
  appgw_backend_hostname   = "apim-orders-dev-a1b2.azure-api.net"
  appgw_listener_hostnames = ["OPEN-appgw-listener-hostname"]
}

run "naming" {
  command = plan

  assert {
    condition     = module.virtual_network.resource.name == "vnet-orders-dev" && module.front_door.resource.name == "afd-orders-dev"
    error_message = "Names come from Azure/naming/azurerm: <slug>-<workload>-<stage>."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
    address_space = "10.101.0.0/23"
  }

  assert {
    condition     = module.virtual_network.resource.name == "vnet-orders-tst" && tolist(module.virtual_network.resource.body.properties.addressSpace.addressPrefixes)[0] == "10.101.0.0/23"
    error_message = "The test stage carries its own stage code and its own address range."
  }
}

run "addressing" {
  command = plan

  # decision: virtual-network.addressing.subnets
  assert {
    condition     = jsonencode(sort(keys(module.virtual_network.subnets))) == jsonencode(["apim", "appgw", "function-integration", "private-endpoints", "workload"])
    error_message = "One subnet per stated purpose: appgw, apim, function-integration, workload, private-endpoints."
  }

  # decision: virtual-network.addressing.private_endpoint_subnet_prefix
  assert {
    condition     = tolist(module.virtual_network.subnets["private-endpoints"].resource.body.properties.addressPrefixes)[0] == "10.100.0.0/27"
    error_message = "The private-endpoint subnet is the first /27 of the stage's range."
  }
}

run "security" {
  command = plan

  # decision: virtual-network.security.subnets_expecting_nsg
  assert {
    condition     = alltrue([for s in module.virtual_network.subnets : s.resource.body.properties.networkSecurityGroup != null])
    error_message = "Every subnet carries a network security group."
  }
}

run "network_security_groups" {
  command = plan

  # decision: network-security-group__appgw.rules.subnet_purpose
  assert {
    condition = (
      module.nsg["appgw"].security_rules["allow_front_door"].source_address_prefix == "AzureFrontDoor.Backend" &&
      module.nsg["appgw"].security_rules["deny_all_inbound"].access == "Deny" &&
      module.nsg["appgw"].security_rules["deny_all_inbound"].priority == 4096
    )
    error_message = "The gateway subnet admits Front Door's backend tag and the platform, then denies the rest inbound at 4096."
  }

  # decision: network-security-group__apim.rules.subnet_purpose
  assert {
    condition = (
      module.nsg["apim"].security_rules["allow_appgw"].source_address_prefix == "10.100.0.32/27" &&
      module.nsg["apim"].security_rules["deny_all_inbound"].access == "Deny"
    )
    error_message = "API Management accepts client traffic from the gateway subnet only; everything else inbound is denied."
  }

  # decision: network-security-group__workload.rules.subnet_purpose
  assert {
    condition = (
      module.nsg["workload"].security_rules["allow_vnet_https"].source_address_prefix == "VirtualNetwork" &&
      module.nsg["workload"].security_rules["deny_all_inbound"].access == "Deny" &&
      alltrue([for k, r in module.nsg["workload"].security_rules : r.source_address_prefix != "*" && r.source_address_prefix != "Internet" if r.access == "Allow"])
    )
    error_message = "The workload subnet allows HTTPS from the network, never from * or the internet; the rest is denied inbound."
  }

  # decision: network-security-group__pe.rules.subnet_purpose
  assert {
    condition = (
      module.nsg["pe"].security_rules["deny_internet_outbound"].access == "Deny" &&
      module.nsg["pe"].security_rules["deny_internet_outbound"].destination_address_prefix == "Internet" &&
      module.nsg["pe"].security_rules["deny_all_inbound"].access == "Deny"
    )
    error_message = "The private-endpoint subnet denies the rest inbound and sends nothing to the internet."
  }
}

run "public_ip" {
  command = plan

  # decision: public-ip-address__appgw.address.purpose
  assert {
    condition     = module.public_ip_appgw.name == "pip-orders-dev-appgw"
    error_message = "The address is the Application Gateway's: purpose application_gateway is the name's last part."
  }
}

run "private_dns" {
  command = plan

  # decision: private-dns-zone.zones
  assert {
    condition = jsonencode(sort(keys(module.private_dns_zone))) == jsonencode(sort([
      "privatelink.blob.core.windows.net",
      "privatelink.dfs.core.windows.net",
      "privatelink.queue.core.windows.net",
      "privatelink.azurewebsites.net",
      "privatelink.servicebus.windows.net",
      "privatelink.azure-api.net",
    ]))
    error_message = "One zone per private endpoint kind of the spec, no more and no less."
  }
}

run "application_gateway" {
  command = plan

  # not-testable: application-gateway.gateway.waf_enabled - the gateway module exposes no resource output; the SKU sits in the azapi body, which no output carries
  # not-testable: application-gateway.gateway.waf_mode - the policy module's outputs are names and ids; the mode is inside the azurerm resource it builds
  # not-testable: application-gateway.gateway.capacity_min - autoscale is part of the gateway body, which the module does not output
  # not-testable: application-gateway.gateway.zone_redundant - zones are part of the gateway body and of the public IP module, neither has a resource output
  # not-testable: application-gateway.networking.frontend_exposure - the frontend configuration is part of the gateway body, which the module does not output
  # not-testable: application-gateway.networking.listeners - listeners are part of the gateway body, which the module does not output

  assert {
    condition     = module.application_gateway.name == "agw-orders-dev-appgw"
    error_message = "The gateway name comes from Azure/naming/azurerm."
  }
}

run "front_door" {
  command = plan

  # decision: front-door.profile.sku
  assert {
    condition     = module.front_door.resource.body.sku.name == "Premium_AzureFrontDoor"
    error_message = "Premium: managed rule sets need it."
  }

  # decision: front-door.delivery.origin_connection
  assert {
    condition     = length(module.front_door.frontdoor_origins["appgw"].private_link) == 0 && module.front_door.frontdoor_origins["appgw"].certificate_name_check_enabled == false
    error_message = "Public origin (override): the Application Gateway cannot be reached over Private Link, so the origin carries no private link."
  }

  # decision: front-door.security.waf_enabled
  assert {
    condition     = module.front_door.frontdoor_firewall_policies["waf"].enabled == true
    error_message = "The firewall policy is on."
  }

  # decision: front-door.security.waf_mode
  assert {
    condition     = module.front_door.frontdoor_firewall_policies["waf"].mode == "Prevention"
    error_message = "Prevention blocks; Detection only records."
  }

  # not-testable: front-door.delivery.caching - the module outputs no routes; the cache block is inside azurerm_cdn_frontdoor_route
}
