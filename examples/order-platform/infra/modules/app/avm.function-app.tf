module "naming_function" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_function_private_endpoint" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = concat(var.naming_suffix, ["func"])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "function_plan" {
  source  = "Azure/avm-res-web-serverfarm/azurerm"
  version = "~> 2.0.8"

  name      = module.naming_function.app_service_plan.name
  location  = var.location
  parent_id = var.resource_groups["application"].id

  os_type = "Linux"
  # decision: function-app.hosting.plan_type - flex_consumption
  sku_name = "FC1"
  # decision: function-app.hosting.zone_redundant - false; the module default is true
  zone_balancing_enabled = false

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      metrics               = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}

module "function_app" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.24.1"

  name                     = module.naming_function.function_app.name_unique
  location                 = var.location
  parent_id                = var.resource_groups["application"].id
  kind                     = "functionapp"
  os_type                  = "Linux"
  service_plan_resource_id = module.function_plan.resource_id

  function_app_uses_fc1 = true
  # OPEN (runtime and version)
  fc1_runtime_name    = var.function_runtime_name
  fc1_runtime_version = var.function_runtime_version
  # decision: function-app.hosting.always_ready_instances - 0: scale to zero, the first call after idle waits
  always_ready          = { http = { instance_count = 0 } }
  instance_memory_in_mb = 2048

  # Host storage by identity, never by key (deployment.local_auth: disabled).
  storage_account_name                     = var.host_storage_name
  storage_uses_managed_identity            = true
  storage_user_assigned_identity_client_id = var.function_identity_client_id
  # The second connection, Flex only: the deployment package.
  storage_authentication_type       = "UserAssignedIdentity"
  storage_user_assigned_identity_id = var.function_identity_id
  storage_container_endpoint        = "${var.host_storage_blob_endpoint}${var.host_deployment_container}"

  # decision: function-app.networking.public_network_access - enabled_with_firewall
  # OVERRIDE (default: disabled): Event Grid delivers blob events to the function over its public endpoint.
  # Access is restricted to the AzureEventGrid and ApiManagement service tags; the app is otherwise private
  # (private endpoint below, default action Deny).
  public_network_access_enabled = true
  virtual_network_subnet_id     = var.subnet_ids["function-integration"]
  vnet_route_all_traffic        = true

  private_endpoints = {
    sites = {
      name                          = module.naming_function_private_endpoint.private_endpoint.name
      subresource_name              = "sites"
      subnet_resource_id            = var.subnet_ids["private-endpoints"]
      private_dns_zone_resource_ids = [var.private_dns_zone_ids["privatelink.azurewebsites.net"]]
    }
  }
  private_endpoints_manage_dns_zone_group = true # deployment.private_dns_records: deployment

  managed_identities = {
    user_assigned_resource_ids = [var.function_identity_id]
  }

  https_only = true
  # The SCM default is true.
  ftp_publish_basic_authentication_enabled = false
  scm_publish_basic_authentication_enabled = false

  site_config = {
    minimum_tls_version           = "1.2"
    scm_minimum_tls_version       = "1.2"
    ip_restriction_default_action = "Deny"
    scm_use_main_ip_restriction   = true
    ip_restriction = [
      {
        name        = "allow-event-grid"
        action      = "Allow"
        priority    = 100
        service_tag = "AzureEventGrid"
      },
      {
        name        = "allow-api-management"
        action      = "Allow"
        priority    = 110
        service_tag = "ApiManagement"
      },
    ]
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      logs = [
        { category = "FunctionAppLogs" },
        { category = "AppServiceAuditLogs" },
      ]
      metrics = [{ category = "AllMetrics" }]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
