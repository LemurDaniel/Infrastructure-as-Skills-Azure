output "service_bus_id" {
  description = "Resource id of the Service Bus namespace."
  value       = module.service_bus.resource_id
}

output "service_bus_name" {
  description = "Name of the Service Bus namespace."
  value       = module.naming_service_bus.servicebus_namespace.name_unique
}

output "event_hubs_id" {
  description = "Resource id of the Event Hubs namespace."
  value       = module.event_hubs.resource_id
}

output "event_hubs_principal_id" {
  description = "Principal id of the Event Hubs namespace's system identity, for the archive's role on the data lake."
  value       = nonsensitive(module.event_hubs.resource.identity[0].principal_id)
}

output "event_grid_system_topic_id" {
  description = "Resource id of the Event Grid system topic."
  value       = azurerm_eventgrid_system_topic.this.id
}
