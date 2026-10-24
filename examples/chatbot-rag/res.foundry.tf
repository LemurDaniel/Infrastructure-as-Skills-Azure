# The Foundry account: an AIServices account that can hold projects. The name is the custom
# subdomain, so it is global and carries <UNIQUE_ID_4>.
data "naming_name" "foundry" {
  resource = "Azure::Microsoft.CognitiveServices/accounts::AIServices"
}

resource "azurerm_cognitive_account" "this" {
  name                = data.naming_name.foundry.name
  resource_group_name = var.resource_group_name
  location            = var.location

  kind                  = "AIServices"
  sku_name              = "S0"
  custom_subdomain_name = data.naming_name.foundry.name # required for private endpoints and token auth

  # account.project_management: true. account.projects is [], so no project is created.
  project_management_enabled = true

  # networking.public_network_access: disabled; networking.restrict_outbound: true
  public_network_access_enabled      = false
  outbound_network_access_restricted = true

  # security.local_authentication_disabled: true (the argument is the inverse). Access is Entra ID.
  local_auth_enabled = false

  # security.key_management: platform_managed - no customer_managed_key block.

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# The models are open in the spec (resources.foundry.models.model_deployments): the names and
# versions come from var.model_deployments and are looked up against the region's catalogue
# (az cognitiveservices model list --location <region>), never recalled. Without an entry the
# account is rendered and deploys no model. The rest of the deployment is the spec's.
resource "azurerm_cognitive_deployment" "this" {
  for_each = var.model_deployments

  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id

  model {
    format  = each.value.format
    name    = each.value.name
    version = each.value.version
  }

  sku {
    name     = "DataZoneStandard" # models.deployment_sku
    capacity = 10                 # models.deployment_capacity - quota not checked, see the open entry
  }

  version_upgrade_option = "OnceCurrentVersionExpired" # models.version_upgrade_option
  rai_policy_name        = "Microsoft.DefaultV2"       # models.content_filter
}
