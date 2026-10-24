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

run "runtime" {
  command = plan

  # decision: app-service.runtime.runtime_stack
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].application_stack[0].docker_image_name == var.container_image && azurerm_linux_web_app.this.site_config[0].application_stack[0].docker_registry_url == var.container_registry_url && azurerm_linux_web_app.this.site_config[0].container_registry_use_managed_identity == true
    error_message = "container: the image and registry from the stage file (open in the spec), pulled with the app's identity."
  }

  # decision: app-service.runtime.always_on
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].always_on == true
    error_message = "Stays loaded; no cold start after 20 idle minutes."
  }

  # decision: app-service.runtime.health_check_path
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].health_check_path == null
    error_message = "Empty in the spec: no health check path until the app has one."
  }

  # decision: app-service.runtime.http2_enabled
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].http2_enabled == true
    error_message = "HTTP/2 on."
  }
}
