data "naming_name" "service_plan" {
  resource = "Azure::Microsoft.Web/serverFarms"
}

data "naming_name" "web_app" {
  resource = "Azure::Microsoft.Web/sites"
}

resource "azurerm_service_plan" "this" {
  name                = data.naming_name.service_plan.name
  resource_group_name = var.resource_group_name
  location            = var.location

  os_type                = "Linux"             # hosting.os_type - the web app below is the Linux resource
  sku_name               = var.app_service_sku # hosting.sku, per stage
  zone_balancing_enabled = false               # hosting.zone_redundant
  worker_count           = 1                   # hosting.instance_count

  tags = local.tags
}

resource "azurerm_linux_web_app" "this" {
  name                = data.naming_name.web_app.name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.this.id

  https_only = true # security.https_only

  # networking.public_network_access: disabled - reachable through the private endpoint only.
  public_network_access_enabled = false

  # networking.vnet_integration: true. The argument on the app, not the swift-connection resource:
  # the two fight on every apply.
  virtual_network_subnet_id = azurerm_subnet.this[var.app_integration_subnet].id

  # security.basic_auth_enabled: false - no FTP and no WebDeploy credentials.
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  # Telemetry: the connection string alone is not enough with local authentication off, so the
  # app authenticates with its identity (Monitoring Metrics Publisher, res.roles.tf).
  app_settings = {
    APPLICATIONINSIGHTS_CONNECTION_STRING     = azurerm_application_insights.this.connection_string
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING = "Authorization=AAD"
  }

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on              = true # runtime.always_on
    http2_enabled          = true # runtime.http2_enabled
    vnet_route_all_enabled = true # networking.vnet_route_all

    minimum_tls_version     = "1.2" # security.min_tls_version, the app and its SCM site
    scm_minimum_tls_version = "1.2"
    ftps_state              = "Disabled" # security.ftps_state

    # runtime.health_check_path is empty: no path is checked, and none is invented.

    # The runtime is open in the spec (runtime.runtime_stack / runtime_version). One argument of
    # application_stack is set, chosen by the stack; the rest stay null.
    application_stack {
      dotnet_version = var.runtime_stack == "dotnet" ? var.runtime_version : null
      go_version     = var.runtime_stack == "go" ? var.runtime_version : null
      java_version   = var.runtime_stack == "java" ? var.runtime_version : null
      node_version   = var.runtime_stack == "node" ? var.runtime_version : null
      php_version    = var.runtime_stack == "php" ? var.runtime_version : null
      python_version = var.runtime_stack == "python" ? var.runtime_version : null
    }
  }

  tags = local.tags
}
