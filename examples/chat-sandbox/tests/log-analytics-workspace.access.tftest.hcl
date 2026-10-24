# Plan-only, credential-free: azurerm is mocked, the naming provider stays real so the
# names are asserted as they will be deployed. Terraform has no include, so every test
# file repeats this header. The variables are the sandbox stage file with its placeholders.
mock_provider "azurerm" {
  # Every id the provider is handed must parse: the mock's random string fails the
  # schema validation before any assert runs.
  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id       = "11111111-1111-1111-1111-111111111111"
      subscription_id = "00000000-0000-0000-0000-000000000000"
      object_id       = "22222222-2222-2222-2222-222222222222"
      client_id       = "33333333-3333-3333-3333-333333333333"
    }
  }
}

variables {
  environment            = "sandbox"
  location               = "germanywestcentral"
  workload               = "chat"
  subscription_id        = "00000000-0000-0000-0000-000000000000"
  resource_group_name    = "OPEN-resource-group"
  tags                   = {}
  container_image        = "OPEN-container-image:OPEN-tag"
  container_registry_url = "https://OPEN-container-registry"
  model_deployments = {
    chat      = { model_format = "OpenAI", model_name = "OPEN-chat-model", model_version = "OPEN-model-version" }
    embedding = { model_format = "OpenAI", model_name = "OPEN-embedding-model", model_version = "OPEN-model-version" }
  }
  role_assignments = {
    foundry = [
      { principal = "app-service", role = "Cognitive Services OpenAI User" },
      { principal = "search-service", role = "Cognitive Services OpenAI User" },
    ]
    search-service = [{ principal = "app-service", role = "Search Index Data Reader" }]
    storage-account = [
      { principal = "app-service", role = "Storage Blob Data Contributor" },
      { principal = "search-service", role = "Storage Blob Data Reader" },
    ]
    key-vault = [{ principal = "app-service", role = "Key Vault Secrets User" }]
  }
}

run "access" {
  command = plan

  # decision: log-analytics-workspace.access.public_network_access
  assert {
    condition     = azurerm_log_analytics_workspace.this.internet_ingestion_access_type == "Enabled" && azurerm_log_analytics_workspace.this.internet_query_access_type == "Enabled"
    error_message = "enabled: both switches, ingestion and query - a standalone deployment has no private link scope."
  }

  # decision: log-analytics-workspace.access.local_auth
  assert {
    condition     = azurerm_log_analytics_workspace.this.local_authentication_enabled == false
    error_message = "The workspace key is a non-expiring bearer credential; agents use Entra ID."
  }

  # decision: log-analytics-workspace.access.rbac_only_access
  assert {
    condition     = azurerm_log_analytics_workspace.this.allow_resource_only_permissions == false
    error_message = "Inverted argument: false means workspace RBAC governs reads."
  }
}
