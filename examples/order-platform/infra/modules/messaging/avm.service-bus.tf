module "naming_service_bus" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "naming_private_endpoint" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(["sb", "eh"])

  suffix        = concat(var.naming_suffix, [each.key])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "service_bus" {
  source  = "Azure/avm-res-servicebus-namespace/azurerm"
  version = "~> 0.4.0"

  name                = module.naming_service_bus.servicebus_namespace.name_unique
  location            = var.location
  resource_group_name = var.resource_groups["application"].name

  # decision: service-bus.namespace.sku - forced by network_exposure: private endpoints need Premium
  sku                          = "Premium"
  capacity                     = 1
  premium_messaging_partitions = 1
  minimum_tls_version          = "1.2"
  # deployment.local_auth: disabled - the inverse input; the module default is true
  local_auth_enabled = false
  # No customer-managed key (key_management: platform_managed), so no infrastructure encryption; the module default is true.
  infrastructure_encryption_enabled = false

  # decision: service-bus.namespace.zone_redundant - false; the module has no input for it
  # (Premium is zone redundant by the platform wherever the region has zones).

  # Private only (deployment.network_exposure): a bool on the module, default true.
  # The module refuses default_action Deny without any rule (a precondition), so the ACL stays Allow and the
  # namespace's public network access switch is what closes it: publicNetworkAccess Disabled wins over the ACL.
  public_network_access_enabled = false
  network_rule_config = {
    default_action           = "Allow"
    trusted_services_allowed = false
    cidr_or_ip_rules         = []
  }
  private_endpoints = {
    namespace = {
      name                          = module.naming_private_endpoint["sb"].private_endpoint.name
      subresource_name              = "namespace"
      subnet_resource_id            = var.private_endpoint_subnet_id
      private_dns_zone_resource_ids = [var.private_dns_zone_ids["privatelink.servicebus.windows.net"]]
    }
  }
  private_endpoints_manage_dns_zone_group = true # deployment.private_dns_records: deployment

  # decision: service-bus.entities.queues - payments
  # decision: service-bus.entities.message_ordering - false: no sessions
  # decision: service-bus.entities.duplicate_protection - true: duplicate detection
  queues = {
    payments = {
      name                         = "payments"
      requires_session             = false
      requires_duplicate_detection = true
    }
  }

  # decision: service-bus.entities.topics - orders with the subscriptions billing, shipping, audit
  topics = {
    orders = {
      name                         = "orders"
      support_ordering             = false
      requires_duplicate_detection = true
      subscriptions = {
        for s in ["billing", "shipping", "audit"] : s => {
          name             = s
          requires_session = false
        }
      }
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      # log_groups defaults to allLogs: empty beside the categories, or every log is collected twice.
      log_categories    = ["OperationalLogs", "VNetAndIPFilteringLogs"]
      log_groups        = []
      metric_categories = ["AllMetrics"]
    }
  }

  # deployment.resource_lock: production
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
