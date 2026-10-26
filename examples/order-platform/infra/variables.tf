variable "subscription_id" {
  description = "Subscription of the stage (stage_isolation: subscription). Supplied by environments/<stage>.tfvars."
  type        = string
}

variable "environment" {
  description = "Stage. Drives the rendered names and the production-only locks."
  type        = string

  validation {
    condition     = contains(["development", "test", "production"], var.environment)
    error_message = "environment must be one of development, test, production."
  }
}

variable "location" {
  description = "Azure region of every resource (context.location)."
  type        = string
}

variable "workload" {
  description = "Workload short name, rendered into every resource name (context.workload)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{2,10}$", var.workload))
    error_message = "workload must be 2-10 lowercase letters or digits (storage account names allow 24 characters in total)."
  }
}

variable "tags" {
  description = "Tags on every resource. The spec prescribes no tag set (context.tags is absent), so the stage file decides."
  type        = map(string)
}

variable "address_space" {
  description = "Address range of the stage's virtual network (deployment.address_space), a /23."
  type        = string

  validation {
    condition     = can(cidrhost(var.address_space, 0)) && endswith(var.address_space, "/23")
    error_message = "address_space must be a CIDR range with prefix length /23."
  }
}

variable "lock_enabled" {
  description = "CanNotDelete locks on data-holding resources and on the resource groups (deployment.resource_lock / resource_group_lock: production)."
  type        = bool
}

variable "publisher_name" {
  description = "Organisation name shown in API Management. OPEN in the spec: placeholder OPEN-publisher-name until answered."
  type        = string
}

variable "publisher_email" {
  description = "Contact address for API Management notifications. OPEN in the spec: placeholder OPEN-publisher-email until answered."
  type        = string
}

variable "function_runtime_name" {
  description = "Flex Consumption runtime stack (node, dotnet-isolated, powershell, python, java). OPEN in the spec."
  type        = string
}

variable "function_runtime_version" {
  description = "Runtime version of the function app. OPEN in the spec."
  type        = string
}

variable "appgw_listener_hostnames" {
  description = "Domains of the Application Gateway listeners. OPEN in the spec (listeners: []); the placeholder list renders one scaffold HTTP listener."
  type        = list(string)
}

variable "vm_size" {
  description = "VM size of the three virtual machines. OPEN in the spec (assumption: Standard_D2ds_v5)."
  type        = string
}

variable "vm_admin_ssh_public_key" {
  description = "Public SSH key of the VMs. OPEN in the spec."
  type        = string
}

variable "event_function_name" {
  description = "Name of the function that handles BlobCreated events (Event Grid destination). Not in the spec's open list; placeholder OPEN-function-name until the code is named."
  type        = string
}
