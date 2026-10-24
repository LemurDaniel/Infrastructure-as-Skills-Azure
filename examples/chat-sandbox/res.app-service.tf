# App Service - a Linux plan and the web app running the chat application's container.

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

  # decision: app-service.hosting.os_type - the plan's OS; the app is a Linux web app
  os_type = "Linux"
  # decision: app-service.hosting.sku - B1, the non_production_default a [sandbox] stack takes (forced by environments)
  sku_name = "B1"
  # decision: app-service.hosting.zone_redundant - outage_impact: tolerable
  zone_balancing_enabled = false
  # decision: app-service.hosting.instance_count - outage_impact: tolerable
  worker_count = 1

  tags = local.tags
}

resource "azurerm_linux_web_app" "this" {
  name                = data.naming_name.web_app.name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.this.id

  # decision: app-service.networking.public_network_access - enabled (overridden): users
  # reach the app from the internet, and with no network there is no allowlist to apply.
  public_network_access_enabled = true
  # decision: app-service.networking.vnet_integration - false (network_ownership: none):
  # no virtual_network_subnet_id, outbound traffic leaves over the public internet.

  # decision: app-service.security.https_only
  https_only = true
  # decision: app-service.security.basic_auth_enabled - false (local_auth: disabled). Two
  # switches, FTP and SCM/WebDeploy; both written.
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  # decision: app-service.identity.managed_identity - the identity the role assignments
  # on Foundry, search, storage and the vault are granted to.
  identity {
    type = "SystemAssigned"
  }

  site_config {
    # decision: app-service.runtime.always_on
    always_on = true
    # decision: app-service.runtime.http2_enabled
    http2_enabled = true
    # decision: app-service.runtime.health_check_path - empty: not checked, so omitted.

    # decision: app-service.security.ftps_state
    ftps_state = "Disabled"
    # decision: app-service.security.min_tls_version - the same floor on the Kudu/SCM site
    minimum_tls_version     = "1.2"
    scm_minimum_tls_version = "1.2"

    # public_network_access: enabled - no access restrictions, on the app and on SCM.
    ip_restriction_default_action     = "Allow"
    scm_ip_restriction_default_action = "Allow"
    scm_use_main_ip_restriction       = true

    # decision: app-service.runtime.runtime_stack - container. The image is open in the
    # spec (resources.app-service.runtime.container_image) and comes from the stage file;
    # it is pulled with the app's managed identity, never with an admin user.
    container_registry_use_managed_identity = true
    application_stack {
      docker_image_name   = var.container_image
      docker_registry_url = var.container_registry_url
    }
  }

  tags = local.tags
}

# decision: app-service.observability.diagnostic_categories - the site's log categories
locals {
  app_service_log_categories = [
    "AppServiceHTTPLogs",
    "AppServiceAppLogs",
    "AppServiceAuditLogs",
    "AppServiceIPSecAuditLogs",
    "AppServicePlatformLogs",
  ]
}

resource "azurerm_monitor_diagnostic_setting" "web_app" {
  name                       = "diag"
  target_resource_id         = azurerm_linux_web_app.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(local.app_service_log_categories)
    content {
      category = enabled_log.value
    }
  }

  # decision: app-service.observability.metrics_enabled
  enabled_metric {
    category = "AllMetrics"
  }
}

# The plan has metrics only - CPU and memory are what decide whether B1 is enough.
resource "azurerm_monitor_diagnostic_setting" "service_plan" {
  name                       = "diag"
  target_resource_id         = azurerm_service_plan.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  enabled_metric {
    category = "AllMetrics"
  }
}
