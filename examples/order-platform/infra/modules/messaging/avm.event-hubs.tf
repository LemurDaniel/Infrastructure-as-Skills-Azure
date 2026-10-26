module "naming_event_hubs" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = var.naming_suffix
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "event_hubs" {
  source  = "Azure/avm-res-eventhub-namespace/azurerm"
  version = "~> 0.1.1"

  name                = module.naming_event_hubs.eventhub_namespace.name_unique
  location            = var.location
  resource_group_name = var.resource_groups["application"].name

  # decision: event-hubs.namespace.sku
  sku                  = "Standard"
  capacity             = 1
  auto_inflate_enabled = false
  # deployment.local_auth: disabled - the inverse input
  local_authentication_enabled = false

  # decision: event-hubs.recovery.zone_redundant - false; the module has no input for it.

  # The namespace's own identity writes the archive into the data lake (role in the root's wiring).
  managed_identities = {
    system_assigned = true
  }

  # Private only (deployment.network_exposure): a bool on the module. The trusted-service bypass stays on so
  # the archive (capture) can reach the private data lake.
  public_network_access_enabled = false
  network_rulesets = {
    default_action                 = "Deny"
    public_network_access_enabled  = false
    trusted_service_access_enabled = true
    ip_rule                        = []
  }
  private_endpoints = {
    namespace = {
      name                          = module.naming_private_endpoint["eh"].private_endpoint.name
      subresource_name              = "namespace"
      subnet_resource_id            = var.private_endpoint_subnet_id
      private_dns_zone_resource_ids = [var.private_dns_zone_ids["privatelink.servicebus.windows.net"]]
    }
  }
  private_endpoints_manage_dns_zone_group = true # deployment.private_dns_records: deployment

  # decision: event-hubs.entities.event_hubs - telemetry
  # decision: event-hubs.entities.event_archive - true: capture to the data lake
  # decision: event-hubs.entities.archive_storage_account - storage-account__datalake
  event_hubs = {
    telemetry = {
      namespace_name      = module.naming_event_hubs.eventhub_namespace.name_unique
      resource_group_name = var.resource_groups["application"].name
      partition_count     = 2
      message_retention   = 1
      capture_description = {
        enabled             = true
        encoding            = "Avro"
        interval_in_seconds = 300
        skip_empty_archives = true
        destination = {
          name                = "EventHubArchive.AzureBlockBlob"
          archive_name_format = "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"
          blob_container_name = var.datalake_telemetry_container
          storage_account_id  = var.datalake_id
        }
      }
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["OperationalLogs", "EventHubVNetConnectionEvent"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  # deployment.resource_lock: production
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
