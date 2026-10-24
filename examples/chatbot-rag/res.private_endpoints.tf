locals {
  # networking.private_endpoint_subresources of the storage account; each needs a zone below.
  storage_private_endpoint_subresources = ["blob"]
  storage_subresource_zone              = { blob = "blob" }

  # One endpoint per resource and sub-resource. The key becomes the <?SUBNAME> of the endpoint's
  # name; zones are the keys of local.private_dns_zones that the endpoint's zone group registers in.
  # The application insights endpoint is not rendered: its Azure Monitor Private Link Scope is
  # open in the spec (resources.application-insights.networking.private_link_scope).
  private_endpoints = merge(
    {
      for s in local.storage_private_endpoint_subresources : "storage-${s}" => {
        resource_id = azurerm_storage_account.this.id
        subresource = s
        subnet      = var.private_endpoint_subnets.storage_account
        zones       = [local.storage_subresource_zone[s]]
      }
    },
    {
      key-vault = {
        resource_id = azurerm_key_vault.this.id
        subresource = "vault"
        subnet      = var.private_endpoint_subnets.key_vault
        zones       = ["vault"]
      }
      foundry = {
        resource_id = azurerm_cognitive_account.this.id
        subresource = "account"
        subnet      = var.private_endpoint_subnets.foundry
        zones       = ["cognitiveservices", "openai", "aiservices"]
      }
      search = {
        resource_id = azurerm_search_service.this.id
        subresource = "searchService"
        subnet      = var.private_endpoint_subnets.search_service
        zones       = ["search"]
      }
      app-service = {
        resource_id = azurerm_linux_web_app.this.id
        subresource = "sites"
        subnet      = var.private_endpoint_subnets.app_service
        zones       = ["sites"]
      }
    }
  )
}

# One name per endpoint through the convention's <?SUBNAME;-%s> token, so the index stays last:
# pep-we-<stage>-chatrag-key-vault-01.
data "naming_name" "private_endpoint" {
  for_each = local.private_endpoints

  resource   = "Azure::Microsoft.Network/privateEndpoints"
  parameters = { subname = each.key }
}

resource "azurerm_private_endpoint" "this" {
  for_each = local.private_endpoints

  name                = data.naming_name.private_endpoint[each.key].name
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.this[each.value.subnet].id

  private_service_connection {
    name                           = "psc-${each.key}"
    private_connection_resource_id = each.value.resource_id
    subresource_names              = [each.value.subresource] # exactly one per endpoint
    is_manual_connection           = false
  }

  # private_dns_ownership: deployment - the zone group is ours, not a policy's.
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [for z in each.value.zones : azurerm_private_dns_zone.this[z].id]
  }

  tags = local.tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.this]
}
