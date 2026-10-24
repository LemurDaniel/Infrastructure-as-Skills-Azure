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

run "models" {
  command = plan

  # The deployments themselves are open in the spec (model_deployments) and come from the
  # stage file as placeholders; the four decisions below hold for every entry.

  # decision: foundry.models.deployment_sku
  assert {
    condition     = alltrue([for d in azurerm_cognitive_deployment.this : d.sku[0].name == "DataZoneStandard"])
    error_message = "data_residency: data_zone - prompts are processed inside the EU data zone, never GlobalStandard."
  }

  # decision: foundry.models.deployment_capacity
  assert {
    condition     = alltrue([for d in azurerm_cognitive_deployment.this : d.sku[0].capacity == 10]) && length(azurerm_cognitive_deployment.this) == 2
    error_message = "10 thousand tokens per minute per deployment, on both stage-file entries."
  }

  # decision: foundry.models.version_upgrade_option
  assert {
    condition     = alltrue([for d in azurerm_cognitive_deployment.this : d.version_upgrade_option == "OnceCurrentVersionExpired"])
    error_message = "The pinned version holds until the platform retires it."
  }

  # decision: foundry.models.content_filter
  assert {
    condition     = alltrue([for d in azurerm_cognitive_deployment.this : d.rai_policy_name == "Microsoft.DefaultV2"])
    error_message = "Every deployment runs behind the built-in Microsoft.DefaultV2 policy."
  }
}
