module "virtual_network" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "~> 0.22.3"

  name      = module.naming.virtual_network.name
  location  = var.location
  parent_id = var.resource_groups["network"].id

  # decision: virtual-network.addressing.address_space (deployment.address_space, per stage)
  address_space = [var.address_space]

  # decision: virtual-network.addressing.subnets
  subnets = {
    for name, prefix in local.subnet_prefixes : name => {
      name             = name
      address_prefixes = [prefix]

      # decision: virtual-network.security.subnets_expecting_nsg
      network_security_group = { id = module.nsg[local.subnet_nsg[name]].resource_id }

      # Enabled, so the subnet's NSG applies to private endpoint traffic.
      private_endpoint_network_policies = "Enabled"
      service_endpoints                 = []
      # Private subnet: no implicit outbound internet access.
      default_outbound_access_enabled = false

      # Flex Consumption integrates through a subnet delegated to Microsoft.App/environments.
      delegations = name == "function-integration" ? [{
        name               = "flex-consumption"
        service_delegation = { name = "Microsoft.App/environments" }
      }] : []
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
