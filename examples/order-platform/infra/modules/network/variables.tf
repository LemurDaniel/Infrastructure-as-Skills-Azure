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
  description = "Created resource groups by role (name and id). This family uses network and main."
  type = map(object({
    name = string
    id   = string
  }))
}

variable "address_space" {
  description = "Address range of the stage's virtual network, a /23 (deployment.address_space)."
  type        = string
}

variable "appgw_identity_id" {
  description = "Resource id of the Application Gateway's user-assigned identity (security family)."
  type        = string
}

variable "appgw_backend_hostname" {
  description = "Hostname of the Application Gateway backend: the API Management gateway (<apim name>.azure-api.net)."
  type        = string
}

variable "appgw_listener_hostnames" {
  description = "Domains of the Application Gateway listeners. OPEN in the spec: a placeholder renders one scaffold HTTP listener."
  type        = list(string)
}
