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

run "observability" {
  command = plan

  # not-testable: storage-account.observability.diagnostic_workspace - the workspace is created in
  # this same root, so its id is unknown at plan time under a mocked provider (Terraform
  # 1.9 has no override_during = plan); the setting's log_analytics_workspace_id cannot be
  # compared. The target is azurerm_log_analytics_workspace.this.id in the code, by reference.

  # decision: storage-account.observability.diagnostic_categories
  assert {
    condition     = toset([for l in azurerm_monitor_diagnostic_setting.storage_blob.enabled_log : l.category_group]) == toset(["audit"]) && length(azurerm_monitor_diagnostic_setting.storage_account.enabled_log) == 0
    error_message = "audit on the blob service; the account itself emits no log categories."
  }

  # decision: storage-account.observability.metrics_enabled
  assert {
    condition     = [for m in azurerm_monitor_diagnostic_setting.storage_account.enabled_metric : m.category][0] == "AllMetrics" && [for m in azurerm_monitor_diagnostic_setting.storage_blob.enabled_metric : m.category][0] == "AllMetrics"
    error_message = "AllMetrics on both targets."
  }
}
