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
  description = "Created resource groups by role (name and id). This family uses data."
  type = map(object({
    name = string
    id   = string
  }))
}

variable "lock_enabled" {
  description = "CanNotDelete lock on the storage accounts (deployment.resource_lock: production)."
  type        = bool
}

variable "private_endpoint_subnet_id" {
  description = "Subnet for the private endpoints (network family)."
  type        = string
}

variable "private_dns_zone_ids" {
  description = "Private DNS zone ids by zone name (network family); the endpoints attach them through their zone groups."
  type        = map(string)
}

variable "diagnostic_workspace_id" {
  description = "Log Analytics workspace the diagnostic settings write to (observability family)."
  type        = string
}
