# Apply against a mocked azurerm provider: no credentials, nothing deployed. A plan leaves every id of
# a new resource unknown, so the asserts that compare ids need the mock's values. The naming provider
# is real, so names are asserted as they will be deployed; every mocked id parses.
mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id       = "22222222-2222-2222-2222-222222222222"
      subscription_id = "11111111-1111-1111-1111-111111111111"
      object_id       = "33333333-3333-3333-3333-333333333333"
      client_id       = "44444444-4444-4444-4444-444444444444"
    }
  }
  mock_resource "azurerm_log_analytics_workspace" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.OperationalInsights/workspaces/log-mock" }
  }
  mock_resource "azurerm_application_insights" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Insights/components/appi-mock" }
  }
  mock_resource "azurerm_virtual_network" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/virtualNetworks/vnet-mock" }
  }
  mock_resource "azurerm_subnet" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/virtualNetworks/vnet-mock/subnets/snet-mock" }
  }
  mock_resource "azurerm_network_security_group" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/networkSecurityGroups/nsg-mock" }
  }
  mock_resource "azurerm_private_dns_zone" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/privateDnsZones/privatelink.mock.net" }
  }
  mock_resource "azurerm_key_vault" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.KeyVault/vaults/kv-mock" }
  }
  mock_resource "azurerm_storage_account" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Storage/storageAccounts/stmock" }
  }
  mock_resource "azurerm_cognitive_account" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.CognitiveServices/accounts/aif-mock" }
  }
  mock_resource "azurerm_search_service" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Search/searchServices/srch-mock" }
  }
  mock_resource "azurerm_service_plan" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Web/serverFarms/plan-mock" }
  }
  mock_resource "azurerm_linux_web_app" {
    defaults = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Web/sites/app-mock" }
  }
}

# Computed ids are unknown in a plan: the ones the asserts compare are given distinct, parseable values.
override_resource {
  target = azurerm_subnet.this["snet-endpoints"]
  values = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/virtualNetworks/vnet-mock/subnets/snet-endpoints" }
}
override_resource {
  target = azurerm_subnet.this["snet-web"]
  values = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/virtualNetworks/vnet-mock/subnets/snet-web" }
}
override_resource {
  target = azurerm_network_security_group.this["endpoints"]
  values = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/networkSecurityGroups/nsg-endpoints" }
}
override_resource {
  target = azurerm_network_security_group.this["integration"]
  values = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.Network/networkSecurityGroups/nsg-integration" }
}
override_resource {
  target = azurerm_log_analytics_workspace.this
  values = { id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-mock/providers/Microsoft.OperationalInsights/workspaces/log-mock" }
}

# The production stage with parseable mock values; the placeholders of environments/*.tfvars
# never reach a plan. Model and runtime values are mocks, not answers to the open entries.
variables {
  subscription_id     = "11111111-1111-1111-1111-111111111111"
  resource_group_name = "rg-mock"
  location            = "westeurope"
  workload            = "chatrag"
  environment         = "production"
  tags                = {}

  address_space = "10.20.0.0/16"
  subnets = {
    "snet-endpoints" = { prefix = "10.20.1.0/27" }
    "snet-web"       = { prefix = "10.20.2.0/26" }
  }
  dns_servers            = []
  subnets_expecting_nsg  = ["snet-endpoints", "snet-web"]
  app_integration_subnet = "snet-web"
  private_endpoint_subnets = {
    key_vault       = "snet-endpoints"
    storage_account = "snet-endpoints"
    foundry         = "snet-endpoints"
    search_service  = "snet-endpoints"
    app_service     = "snet-endpoints"
  }
  endpoints_nsg_rules   = []
  integration_nsg_rules = []

  role_assignments = [
    { resource = "application-insights", principal = "app-service", role = "Monitoring Metrics Publisher" },
    { resource = "storage-account", principal = "search-service", role = "Storage Blob Data Reader" },
    { resource = "foundry", principal = "app-service", role = "Cognitive Services OpenAI User" },
    { resource = "foundry", principal = "search-service", role = "Cognitive Services OpenAI User" },
    { resource = "search-service", principal = "app-service", role = "Search Index Data Reader" },
  ]

  search_sku      = "standard"
  app_service_sku = "P1v3"

  model_deployments = {
    chat      = { name = "mock-chat-model", version = "mock-version" }
    embedding = { name = "mock-embedding-model", version = "mock-version" }
  }
  runtime_stack   = "node"
  runtime_version = "20-lts"
}

run "vault" {
  command = apply

  # decision: key-vault.vault.sku
  assert {
    condition     = azurerm_key_vault.this.sku_name == "standard"
    error_message = "Standard SKU."
  }

  # decision: key-vault.vault.purge_protection
  assert {
    condition     = azurerm_key_vault.this.purge_protection_enabled == true
    error_message = "Purge protection on."
  }

  # decision: key-vault.vault.soft_delete_retention_days
  assert {
    condition     = azurerm_key_vault.this.soft_delete_retention_days == 90
    error_message = "Soft delete 90 days."
  }

  # decision: key-vault.vault.rbac_authorization
  assert {
    condition     = azurerm_key_vault.this.rbac_authorization_enabled == true
    error_message = "RBAC, no access policies."
  }
}
