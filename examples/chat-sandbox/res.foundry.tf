# AI Foundry - an AI Services account with projects and the model deployments.

# ::AIServices selects the kind's abbreviation (aif) from naming.yaml.
data "naming_name" "foundry" {
  resource = "Azure::Microsoft.CognitiveServices/accounts::AIServices"
}

# One name per project through the convention, with the project's own name as <NAME>.
data "naming_name" "foundry_project" {
  for_each = toset(local.foundry_projects)

  resource   = "Azure::Microsoft.CognitiveServices/accounts/projects"
  parameters = { name = each.key }
}

locals {
  # decision: foundry.account.projects
  foundry_projects = ["chat"]
}

resource "azurerm_cognitive_account" "this" {
  name                = data.naming_name.foundry.name
  resource_group_name = var.resource_group_name
  location            = var.location

  # decision: foundry.account.kind - the Foundry resource; fixed at creation
  kind = "AIServices"
  # decision: foundry.account.sku_name
  sku_name = "S0"
  # The hostname - required for token authentication and for projects; fixed at creation.
  custom_subdomain_name = data.naming_name.foundry.name
  # decision: foundry.account.project_management
  project_management_enabled = true

  # decision: foundry.networking.public_network_access - enabled (overridden): the app
  # and the search service call the models from public, changing addresses.
  public_network_access_enabled = true
  # decision: foundry.networking.restrict_outbound - the account calls out only to
  # names that are explicitly allowed, and none is named: the exfiltration path is shut.
  outbound_network_access_restricted = true

  # decision: foundry.identity.managed_identity
  identity {
    type = "SystemAssigned"
  }

  # decision: foundry.security.local_authentication_disabled - inverse argument; callers
  # hold a role and a token for the custom subdomain.
  local_auth_enabled = false
  # decision: foundry.security.key_management - platform_managed: no customer_managed_key

  tags = local.tags
}

resource "azurerm_cognitive_account_project" "this" {
  for_each = toset(local.foundry_projects)

  name                 = data.naming_name.foundry_project[each.key].name
  display_name         = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id
  location             = var.location

  # A project's connections use its own identity; their roles are a pattern's wiring.
  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# One deployment per entry of the stage file. The models are open in the spec
# (resources.foundry.models.model_deployments); the decisions below hold for every entry.
resource "azurerm_cognitive_deployment" "this" {
  for_each = var.model_deployments

  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id

  model {
    format  = each.value.model_format
    name    = each.value.model_name
    version = each.value.model_version
  }

  sku {
    # decision: foundry.models.deployment_sku - DataZoneStandard: prompts are processed
    # inside the EU data zone (data_residency: data_zone), never anywhere in the world.
    name = "DataZoneStandard"
    # decision: foundry.models.deployment_capacity - thousands of tokens per minute; a
    # rate limit counted against the subscription's quota, not a cost.
    capacity = 10
  }

  # decision: foundry.models.version_upgrade_option - the pinned version holds until the
  # platform retires it, then moves rather than stops.
  version_upgrade_option = "OnceCurrentVersionExpired"
  # decision: foundry.models.content_filter
  rai_policy_name = "Microsoft.DefaultV2"
}

# decision: foundry.observability.diagnostic_categories
locals {
  foundry_log_categories = ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"]
}

resource "azurerm_monitor_diagnostic_setting" "foundry" {
  name                       = "diag"
  target_resource_id         = azurerm_cognitive_account.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(local.foundry_log_categories)
    content {
      category = enabled_log.value
    }
  }

  # decision: foundry.observability.metrics_enabled
  enabled_metric {
    category = "AllMetrics"
  }
}
