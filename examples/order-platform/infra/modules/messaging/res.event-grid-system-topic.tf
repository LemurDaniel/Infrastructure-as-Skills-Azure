# Event Grid system topic on the data lake. Authored: the AVM module avm-res-eventgrid-systemtopic is Proposed,
# not published (implementation: authored). Written for azurerm 4.x, which the other AVM modules pin.

module "naming_system_topic" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  suffix        = concat(var.naming_suffix, ["dl"])
  unique-seed   = var.unique_seed
  unique-length = 4
}

resource "azurerm_eventgrid_system_topic" "this" {
  name                = module.naming_system_topic.eventgrid_system_topic.name
  resource_group_name = var.resource_groups["application"].name
  # The source's region (the data lake lives in context.location).
  location = var.location

  # decision: event-grid-system-topic.source.source_resource - fixed at creation
  source_resource_id = var.datalake_id
  # decision: event-grid-system-topic.source.topic_type - fixed at creation, exact casing
  topic_type = "Microsoft.Storage.StorageAccounts"

  tags = var.tags
}

resource "azurerm_eventgrid_system_topic_event_subscription" "blob_created" {
  name                = "blob-created-to-function"
  system_topic        = azurerm_eventgrid_system_topic.this.name
  resource_group_name = var.resource_groups["application"].name

  # decision: event-grid-system-topic.delivery.destination_kind - azure_function
  # Delivery goes over the function's public endpoint, which admits only the AzureEventGrid service tag
  # (the function app's public_network_access override).
  azure_function_endpoint {
    function_id = "${var.function_app_id}/functions/${var.event_function_name}"
  }

  event_delivery_schema = "EventGridSchema"
  # decision: event-grid-system-topic.delivery.included_event_types - assumed: only new blobs
  included_event_types = ["Microsoft.Storage.BlobCreated"]

  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440
  }
}
