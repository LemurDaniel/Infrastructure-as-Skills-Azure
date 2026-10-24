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

run "data_protection" {
  command = plan

  # decision: storage-account.data_protection.replication
  assert {
    condition     = azurerm_storage_account.this.account_replication_type == "LRS"
    error_message = "outage_impact: tolerable - LRS."
  }

  # decision: storage-account.data_protection.access_tier
  assert {
    condition     = azurerm_storage_account.this.access_tier == "Hot"
    error_message = "data_access_pattern: active - Hot."
  }

  # decision: storage-account.data_protection.blob_soft_delete_days
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].delete_retention_policy[0].days == 7
    error_message = "data_loss_tolerance: one_week - blob soft delete 7 days."
  }

  # decision: storage-account.data_protection.container_soft_delete_days
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].container_delete_retention_policy[0].days == 7
    error_message = "data_loss_tolerance: one_week - container soft delete 7 days."
  }

  # decision: storage-account.data_protection.versioning_enabled
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].versioning_enabled == true
    error_message = "Versioning on: protects against overwrite, which soft delete does not."
  }

  # decision: storage-account.data_protection.change_feed_enabled
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].change_feed_enabled == false
    error_message = "Change feed off unless something consumes it."
  }

  # decision: storage-account.data_protection.point_in_time_restore_days
  assert {
    condition     = length(azurerm_storage_account.this.blob_properties[0].restore_policy) == 0
    error_message = "Point-in-time restore off: no restore_policy block."
  }

  # decision: storage-account.data_protection.immutability
  assert {
    condition     = length(azurerm_storage_account.this.immutability_policy) == 0
    error_message = "No WORM policy unless a mandate names one."
  }
}
