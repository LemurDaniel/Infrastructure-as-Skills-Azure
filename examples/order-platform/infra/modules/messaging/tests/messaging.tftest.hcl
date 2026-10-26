# Messaging family, planned alone: `terraform -chdir=modules/messaging test`.
# Service Bus is azurerm-based (its outputs are the azurerm resources), Event Hubs is AzAPI-based (bodies),
# the system topic is authored (plain azurerm resources).

mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000000"
      tenant_id       = "00000000-0000-0000-0000-000000000000"
      object_id       = "00000000-0000-0000-0000-000000000000"
      client_id       = "00000000-0000-0000-0000-000000000000"
    }
  }
}
mock_provider "azapi" {}
mock_provider "modtm" {}
mock_provider "random" {}

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  lock_enabled  = false
  resource_groups = {
    application = {
      name = "rg-orders-dev-application"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-application"
    }
  }
  private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/private-endpoints"
  private_dns_zone_ids = {
    "privatelink.servicebus.windows.net" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Network/privateDnsZones/privatelink.servicebus.windows.net"
  }
  diagnostic_workspace_id      = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-observability/providers/Microsoft.OperationalInsights/workspaces/log-orders-dev"
  datalake_id                  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-data/providers/Microsoft.Storage/storageAccounts/stordersdevdla1b2"
  datalake_telemetry_container = "telemetry"
  function_app_id              = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-application/providers/Microsoft.Web/sites/func-orders-dev-a1b2"
  event_function_name          = "OnBlobCreated"
}

run "naming" {
  command = plan

  assert {
    condition     = module.service_bus.resource.name == "sb-orders-dev-a1b2" && azurerm_eventgrid_system_topic.this.name == "egst-orders-dev-dl"
    error_message = "Names come from Azure/naming/azurerm; global names carry the 4-character suffix."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
  }

  assert {
    condition     = module.service_bus.resource.name == "sb-orders-tst-a1b2"
    error_message = "The test stage carries its own stage code."
  }
}

run "service_bus" {
  command = plan

  # decision: service-bus.namespace.sku
  assert {
    condition     = module.service_bus.resource.sku == "Premium"
    error_message = "Premium: private endpoints need it."
  }

  # not-testable: service-bus.namespace.zone_redundant - the module has no input for zone redundancy; Premium is zone redundant wherever the region has zones
  # decision: service-bus.entities.topics
  assert {
    condition = (
      jsonencode(keys(module.service_bus.resource_topics)) == jsonencode(["orders"]) &&
      jsonencode(sort(keys(module.service_bus.resource_topics_subscriptions))) == jsonencode(["orders|audit", "orders|billing", "orders|shipping"])
    )
    error_message = "One topic, orders, with the subscriptions billing, shipping and audit."
  }

  # decision: service-bus.entities.queues
  assert {
    condition     = jsonencode(keys(module.service_bus.resource_queues)) == jsonencode(["payments"])
    error_message = "One queue: payments."
  }

  # decision: service-bus.entities.message_ordering
  assert {
    condition = (
      module.service_bus.resource_queues["payments"].requires_session == false &&
      alltrue([for k, s in module.service_bus.resource_topics_subscriptions : s.requires_session == false])
    )
    error_message = "No sessions: message ordering is not required."
  }

  # decision: service-bus.entities.duplicate_protection
  assert {
    condition = (
      module.service_bus.resource_queues["payments"].requires_duplicate_detection == true &&
      module.service_bus.resource_topics["orders"].requires_duplicate_detection == true
    )
    error_message = "Duplicate detection on the queue and the topic."
  }
}

run "event_hubs" {
  command = plan

  # not-testable: event-hubs.namespace.sku - the namespace's attributes are known only after apply (the module reads them back from the API); the call writes sku = "Standard"

  # decision: event-hubs.entities.event_hubs
  assert {
    condition     = jsonencode(keys(module.event_hubs.resource_eventhubs)) == jsonencode(["telemetry"])
    error_message = "One event hub: telemetry."
  }

  # decision: event-hubs.entities.event_archive
  assert {
    condition     = module.event_hubs.resource_eventhubs["telemetry"].capture_description[0].enabled == true
    error_message = "The archive (capture) is on."
  }

  # decision: event-hubs.entities.archive_storage_account
  assert {
    condition     = module.event_hubs.resource_eventhubs["telemetry"].capture_description[0].destination[0].storage_account_id == var.datalake_id
    error_message = "The archive goes to the data lake."
  }

  # not-testable: event-hubs.recovery.zone_redundant - the module has no input for zone redundancy
}

run "event_grid_system_topic" {
  command = plan

  # decision: event-grid-system-topic.source.topic_type
  assert {
    condition     = azurerm_eventgrid_system_topic.this.topic_type == "Microsoft.Storage.StorageAccounts"
    error_message = "Blob events of a storage account."
  }

  # decision: event-grid-system-topic.source.source_resource
  assert {
    condition     = azurerm_eventgrid_system_topic.this.source_resource_id == var.datalake_id
    error_message = "The source is the data lake."
  }

  # decision: event-grid-system-topic.delivery.destination_kind
  assert {
    condition     = length(azurerm_eventgrid_system_topic_event_subscription.blob_created.azure_function_endpoint) == 1 && length(azurerm_eventgrid_system_topic_event_subscription.blob_created.webhook_endpoint) == 0
    error_message = "The destination is an Azure function."
  }

  # decision: event-grid-system-topic.delivery.included_event_types
  assert {
    condition     = jsonencode(azurerm_eventgrid_system_topic_event_subscription.blob_created.included_event_types) == jsonencode(["Microsoft.Storage.BlobCreated"])
    error_message = "Only new blobs (assumed event type)."
  }
}
