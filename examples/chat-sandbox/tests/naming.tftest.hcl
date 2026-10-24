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

run "naming" {
  command = plan

  # The naming provider is not mocked: the names are asserted as they will be deployed
  # for the sandbox stage (sbx, gwc), which is also the test that catches an edited
  # naming.yaml. Global names carry <UNIQUE_ID_4> from the seed subscription/resource group.
  assert {
    condition     = azurerm_service_plan.this.name == "plan-gwc-sbx-chat-01"
    error_message = "The plan name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_linux_web_app.this.name == "app-gwc-sbx-chat-01"
    error_message = "The app name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_cognitive_account.this.name == "aif-sbx-chat-92f8" && azurerm_cognitive_account.this.custom_subdomain_name == "aif-sbx-chat-92f8"
    error_message = "The Foundry account name (and its subdomain) must come from naming.yaml with the AIServices abbreviation."
  }

  assert {
    condition     = azurerm_cognitive_account_project.this["chat"].name == "proj-gwc-sbx-chat-01"
    error_message = "The project name must come from naming.yaml with the project's own name as <NAME>."
  }

  assert {
    condition     = azurerm_search_service.this.name == "srch-sbx-chat-92f8"
    error_message = "The search service name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_storage_account.this.name == "stgwcsbxchat01"
    error_message = "The storage account name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_key_vault.this.name == "kv-sbx-chat-92f8"
    error_message = "The key vault name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_log_analytics_workspace.this.name == "log-gwc-sbx-chat-01"
    error_message = "The workspace name must come from naming.yaml, not from a literal."
  }
}
