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
  description = "CanNotDelete lock on both vaults (deployment.resource_lock: production)."
  type        = bool
}

variable "diagnostic_workspace_id" {
  description = "Log Analytics workspace the diagnostic settings write to (observability family)."
  type        = string
}

variable "datalake_id" {
  description = "Resource id of the data lake storage account, protected by the Backup vault (data family)."
  type        = string
}

variable "datalake_container_names" {
  description = "Containers of the data lake the Backup vault protects."
  type        = list(string)
}

variable "vm_ids" {
  description = "Resource ids of the virtual machines by instance number, protected by the Recovery Services vault (app family)."
  type        = map(string)
}

variable "vm_ready_ids" {
  description = "Resource ids of the virtual machines as created (known after apply). Only orders the protection items behind the machines; vm_ids carries the ids the vault is given."
  type        = map(string)
}
