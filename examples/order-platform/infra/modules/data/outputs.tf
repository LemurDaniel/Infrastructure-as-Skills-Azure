output "datalake_id" {
  description = "Resource id of the data lake storage account."
  value       = module.storage_datalake.resource_id
}

output "datalake_name" {
  description = "Name of the data lake storage account."
  value       = module.storage_datalake.name
}

output "host_storage_id" {
  description = "Resource id of the function app's host storage account."
  value       = module.storage_host.resource_id
}

output "host_storage_name" {
  description = "Name of the host storage account."
  value       = module.storage_host.name
}

output "host_storage_blob_endpoint" {
  description = "Blob endpoint of the host storage account, with trailing slash."
  value       = "https://${module.storage_host.name}.blob.core.windows.net/"
}

output "host_deployment_container" {
  description = "Container that holds the Flex Consumption deployment package."
  value       = "app-package"
}

output "datalake_telemetry_container" {
  description = "Container of the Event Hubs archive."
  value       = "telemetry"
}
