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

run "hosting" {
  command = plan

  # decision: app-service.hosting.os_type
  assert {
    condition     = azurerm_service_plan.this.os_type == "Linux"
    error_message = "Linux plan; the app is an azurerm_linux_web_app, which is the same choice."
  }

  # decision: app-service.hosting.sku
  assert {
    condition     = azurerm_service_plan.this.sku_name == "B1"
    error_message = "B1, the non_production_default a [sandbox] stack takes - forced by deployment.environments."
  }

  # decision: app-service.hosting.zone_redundant
  assert {
    condition     = azurerm_service_plan.this.zone_balancing_enabled == false
    error_message = "outage_impact: tolerable - not zone redundant."
  }

  # decision: app-service.hosting.instance_count
  assert {
    condition     = azurerm_service_plan.this.worker_count == 1
    error_message = "outage_impact: tolerable - one instance."
  }
}
