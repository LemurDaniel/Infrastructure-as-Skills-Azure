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

run "account" {
  command = plan

  # decision: foundry.account.kind
  assert {
    condition     = azurerm_cognitive_account.this.kind == "AIServices"
    error_message = "The Foundry resource, not a classic OpenAI account."
  }

  # decision: foundry.account.sku_name
  assert {
    condition     = azurerm_cognitive_account.this.sku_name == "S0"
    error_message = "S0 is the only tier that takes projects and real deployments."
  }

  # decision: foundry.account.project_management
  assert {
    condition     = azurerm_cognitive_account.this.project_management_enabled == true
    error_message = "The account holds Foundry projects."
  }

  # decision: foundry.account.projects
  assert {
    condition     = length(azurerm_cognitive_account_project.this) == 1 && azurerm_cognitive_account_project.this["chat"].display_name == "chat" && azurerm_cognitive_account_project.this["chat"].identity[0].type == "SystemAssigned"
    error_message = "One project, chat, with its own identity."
  }
}
