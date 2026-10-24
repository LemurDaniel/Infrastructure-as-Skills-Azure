# private_dns_ownership: deployment - the zones, their links to the network and the zone groups at
# the private endpoints (res.private_endpoints.tf) belong to this deployment, not to a platform policy.
resource "azurerm_private_dns_zone" "this" {
  for_each = local.private_dns_zones

  name                = each.value
  resource_group_name = var.resource_group_name

  tags = local.tags
}

# The link name has no convention type in naming.yaml; it is derived from the rendered network name.
resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each = local.private_dns_zones

  name                 = "link-${each.key}-${azurerm_virtual_network.this.name}"
  private_dns_zone_id  = azurerm_private_dns_zone.this[each.key].id
  virtual_network_id   = azurerm_virtual_network.this.id
  registration_enabled = false # a privatelink zone only resolves; nothing registers into it
  tags                 = local.tags
}
