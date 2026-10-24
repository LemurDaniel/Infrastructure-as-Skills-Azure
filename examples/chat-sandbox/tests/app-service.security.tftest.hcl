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

run "security" {
  command = plan

  # decision: app-service.security.https_only
  assert {
    condition     = azurerm_linux_web_app.this.https_only == true
    error_message = "Plain HTTP is redirected."
  }

  # decision: app-service.security.min_tls_version
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].minimum_tls_version == "1.2" && azurerm_linux_web_app.this.site_config[0].scm_minimum_tls_version == "1.2"
    error_message = "TLS 1.2 is the floor, on the app and on the Kudu/SCM site."
  }

  # decision: app-service.security.ftps_state
  assert {
    condition     = azurerm_linux_web_app.this.site_config[0].ftps_state == "Disabled"
    error_message = "FTP is a credential path next to Entra ID; off."
  }

  # decision: app-service.security.basic_auth_enabled
  assert {
    condition     = azurerm_linux_web_app.this.ftp_publish_basic_authentication_enabled == false && azurerm_linux_web_app.this.webdeploy_publish_basic_authentication_enabled == false
    error_message = "local_auth: disabled - no publishing with the publish profile, on FTP and on SCM."
  }
}
