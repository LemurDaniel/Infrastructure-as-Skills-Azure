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

run "vault" {
  command = plan

  # decision: key-vault.vault.sku
  assert {
    condition     = azurerm_key_vault.this.sku_name == "standard"
    error_message = "standard: no HSM mandate (key_protection: software), premium buys nothing."
  }

  # decision: key-vault.vault.purge_protection
  assert {
    condition     = azurerm_key_vault.this.purge_protection_enabled == false
    error_message = "Purge protection off - overridden for a throwaway sandbox: once on it cannot be switched off and reserves the name for the whole retention."
  }

  # decision: key-vault.vault.soft_delete_retention_days
  assert {
    condition     = azurerm_key_vault.this.soft_delete_retention_days == 7
    error_message = "7 days, the shortest window - overridden for a throwaway sandbox; fixed at creation."
  }

  # decision: key-vault.vault.rbac_authorization
  assert {
    condition     = azurerm_key_vault.this.rbac_authorization_enabled == true
    error_message = "local_auth: disabled - role assignments, no access policies."
  }
}
