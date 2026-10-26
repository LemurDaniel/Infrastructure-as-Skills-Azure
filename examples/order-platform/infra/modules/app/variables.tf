variable "environment" {
  description = "Stage (development, test, production)."
  type        = string
}

variable "location" {
  description = "Azure region (context.location)."
  type        = string
}

variable "workload" {
  description = "Workload short name (context.workload)."
  type        = string
}

variable "naming_suffix" {
  description = "Suffix list of Azure/naming/azurerm: workload and stage code."
  type        = list(string)
}

variable "unique_seed" {
  description = "Seed of the 4-character suffix of global names."
  type        = string
}

variable "tags" {
  description = "Tags on every resource."
  type        = map(string)
}

variable "resource_groups" {
  description = "Created resource groups by role (name and id). This family uses application and main."
  type = map(object({
    name = string
    id   = string
  }))
}

variable "apim_name" {
  description = "Name of the API Management service. Resolved in the root because the network family needs it for the gateway backend."
  type        = string
}

variable "subnet_ids" {
  description = "Subnet ids by subnet name (network family)."
  type        = map(string)
}

variable "private_dns_zone_ids" {
  description = "Private DNS zone ids by zone name (network family)."
  type        = map(string)
}

variable "diagnostic_workspace_id" {
  description = "Log Analytics workspace the diagnostic settings write to (observability family)."
  type        = string
}

variable "function_identity_id" {
  description = "Resource id of the function app's user-assigned identity (security family)."
  type        = string
}

variable "function_identity_client_id" {
  description = "Client id of the function app's user-assigned identity (security family)."
  type        = string
}

variable "host_storage_name" {
  description = "Name of the function app's host storage account (data family)."
  type        = string
}

variable "host_storage_blob_endpoint" {
  description = "Blob endpoint of the host storage account, with trailing slash (data family)."
  type        = string
}

variable "host_deployment_container" {
  description = "Container with the Flex Consumption deployment package (data family)."
  type        = string
}

variable "publisher_name" {
  description = "Organisation name shown in API Management. OPEN in the spec."
  type        = string
}

variable "publisher_email" {
  description = "Contact address for API Management notifications. OPEN in the spec."
  type        = string
}

variable "function_runtime_name" {
  description = "Flex Consumption runtime stack. OPEN in the spec."
  type        = string
}

variable "function_runtime_version" {
  description = "Runtime version of the function app. OPEN in the spec."
  type        = string
}

variable "vm_size" {
  description = "VM size. OPEN in the spec."
  type        = string
}

variable "vm_admin_ssh_public_key" {
  description = "Public SSH key of the VMs. OPEN in the spec."
  type        = string
}
