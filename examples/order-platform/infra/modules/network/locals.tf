locals {
  # Subnets cut from the stage's /23. The spec fixes only the private-endpoint subnet
  # (first /27 of the range); the others are laid out behind it, each in its own block.
  subnet_prefixes = {
    private-endpoints    = cidrsubnet(var.address_space, 4, 0) # first /27
    appgw                = cidrsubnet(var.address_space, 4, 1)
    apim                 = cidrsubnet(var.address_space, 4, 2)
    function-integration = cidrsubnet(var.address_space, 4, 3) # Flex Consumption needs at least a /27
    workload             = cidrsubnet(var.address_space, 3, 2)
  }

  # Every subnet carries an NSG. Four NSGs for five subnets: the function integration
  # subnet shares the workload NSG.
  subnet_nsg = {
    private-endpoints    = "pe"
    appgw                = "appgw"
    apim                 = "apim"
    function-integration = "workload"
    workload             = "workload"
  }

  deny_all_inbound = {
    deny_all_inbound = {
      name                       = "deny-all-inbound"
      priority                   = 4096
      direction                  = "Inbound"
      access                     = "Deny"
      protocol                   = "*"
      source_address_prefix      = "*"
      source_port_range          = "*"
      destination_address_prefix = "*"
      destination_port_range     = "*"
    }
  }

  nsg_rules = {
    # Public entry of the gateway: only Front Door's backend addresses may call it (the Front Door id
    # header is checked by the gateway's WAF policy), plus the platform's own traffic.
    appgw = {
      allow_front_door = {
        name                       = "allow-front-door-backend"
        priority                   = 100
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "AzureFrontDoor.Backend"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_ranges    = ["80", "443"]
      }
      allow_gateway_manager = {
        name                       = "allow-gateway-manager"
        priority                   = 110
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "GatewayManager"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_range     = "65200-65535"
      }
      allow_load_balancer = {
        name                       = "allow-azure-load-balancer"
        priority                   = 120
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "*"
        source_address_prefix      = "AzureLoadBalancer"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_range     = "*"
      }
    }

    # Internal API Management: callers are the gateway subnet; the control plane reaches it on 3443.
    apim = {
      allow_appgw = {
        name                       = "allow-appgw-https"
        priority                   = 100
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = local.subnet_prefixes["appgw"]
        source_port_range          = "*"
        destination_address_prefix = "VirtualNetwork"
        destination_port_range     = "443"
      }
      allow_management = {
        name                       = "allow-apim-management"
        priority                   = 110
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "ApiManagement"
        source_port_range          = "*"
        destination_address_prefix = "VirtualNetwork"
        destination_port_range     = "3443"
      }
      allow_load_balancer = {
        name                       = "allow-azure-load-balancer"
        priority                   = 120
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "AzureLoadBalancer"
        source_port_range          = "*"
        destination_address_prefix = "VirtualNetwork"
        destination_port_range     = "6390"
      }
    }

    workload = {
      allow_vnet_https = {
        name                       = "allow-vnet-https"
        priority                   = 100
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "VirtualNetwork"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_range     = "443"
      }
    }

    # Private endpoints: reachable from the network on the service ports, nothing leaves the subnet to the internet.
    pe = {
      allow_vnet_https = {
        name                       = "allow-vnet-https"
        priority                   = 100
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "VirtualNetwork"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_range     = "443"
      }
      allow_vnet_amqp = {
        name                       = "allow-vnet-amqp"
        priority                   = 110
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_address_prefix      = "VirtualNetwork"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_ranges    = ["5671", "5672"]
      }
      deny_internet_outbound = {
        name                       = "deny-internet-outbound"
        priority                   = 4096
        direction                  = "Outbound"
        access                     = "Deny"
        protocol                   = "*"
        source_address_prefix      = "*"
        source_port_range          = "*"
        destination_address_prefix = "Internet"
        destination_port_range     = "*"
      }
    }
  }

  private_dns_zones = [
    "privatelink.blob.core.windows.net",
    "privatelink.dfs.core.windows.net",
    "privatelink.queue.core.windows.net",
    "privatelink.azurewebsites.net",
    "privatelink.servicebus.windows.net",
    "privatelink.azure-api.net",
  ]

  # Application Gateway: the ids of its own sub-objects are built from the gateway's name, because the
  # module takes them before the gateway exists.
  appgw_id = "${var.resource_groups["network"].id}/providers/Microsoft.Network/applicationGateways/${module.naming_appgw.application_gateway.name}"
}
