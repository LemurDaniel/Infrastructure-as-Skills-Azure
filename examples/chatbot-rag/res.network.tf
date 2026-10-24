data "naming_name" "virtual_network" {
  resource = "Azure::Microsoft.Network/virtualNetworks"
}

resource "azurerm_virtual_network" "this" {
  name                = data.naming_name.virtual_network.name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.address_space]

  # Empty: Azure-provided DNS, which resolves the privatelink zones linked in res.dns.tf.
  dns_servers = var.dns_servers

  # No ddos_protection_plan block: a platform decision, not a workload one.

  tags = local.tags
}

# One azurerm_subnet each, never a subnet block on the network: both own the same API field.
# for_each over a map keyed by name, never count: removing one would renumber the next and plan
# a recreate of a subnet that did not change - and a subnet recreate takes its endpoints with it.
resource "azurerm_subnet" "this" {
  for_each = var.subnets

  name                 = each.key
  resource_group_name  = azurerm_virtual_network.this.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [each.value.prefix]

  # Enabled, so the subnet's NSG and routes apply to private endpoint traffic.
  private_endpoint_network_policies = "Enabled"

  # No service endpoints (service_endpoints: []): a private endpoint is the posture, not the
  # weaker service endpoint.

  dynamic "delegation" {
    for_each = [for d in local.subnet_delegations : d if d.subnet == each.key]

    content {
      name = "delegation"
      service_delegation {
        name = delegation.value.service
      }
    }
  }
}

locals {
  # Which group guards which subnet: the endpoints group the private endpoint subnet, the
  # integration group the App Service integration subnet.
  subnet_nsg = {
    "snet-endpoints" = "endpoints"
    "snet-web"       = "integration"
  }
}

# The subnet gets the group that matches its purpose. The azurerm_subnet argument
# network_security_group_id is read-only in azurerm 5.x, so the association is its own resource.
resource "azurerm_subnet_network_security_group_association" "this" {
  for_each = toset(var.subnets_expecting_nsg)

  subnet_id                 = azurerm_subnet.this[each.key].id
  network_security_group_id = azurerm_network_security_group.this[local.subnet_nsg[each.key]].id
}
