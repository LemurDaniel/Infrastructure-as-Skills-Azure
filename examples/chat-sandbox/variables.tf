# Context values are variables with no default; their values come from the stage file
# environments/<stage>.tfvars. Never a literal here, never a value the interview invented.

variable "environment" {
  description = "Deployment stage. Drives the rendered names (mappings.environment in naming.yaml) and the derived tags."
  type        = string

  validation {
    # The keys of mappings.environment in naming.yaml - an environment the convention
    # cannot abbreviate cannot be named.
    condition     = contains(["development", "test", "qa", "uat", "integration", "staging", "preproduction", "production", "sandbox", "demo", "hotfix"], var.environment)
    error_message = "environment must be one of development, test, qa, uat, integration, staging, preproduction, production, sandbox, demo, hotfix."
  }
}

variable "location" {
  description = "Azure region of every resource (context.location). Must be a key of mappings.location in naming.yaml."
  type        = string
}

variable "workload" {
  description = "Workload short name (context.workload), rendered into every resource name as <NAME>."
  type        = string

  validation {
    # The storage account name is <TYPE><LOCATION><ENVIRONMENT><NAME><INDEX> in at most 24
    # lowercase alphanumerics (st + gwc + sbx + name + 01 = 10 + name), and the key vault
    # name kv-<env>-<name>-<4> is at most 24 characters: 12 characters of workload fit both.
    condition     = can(regex("^[a-z0-9]{2,12}$", var.workload))
    error_message = "workload must be 2 to 12 lowercase alphanumeric characters - the storage account and key vault name limits."
  }
}

variable "subscription_id" {
  description = "Subscription the stage deploys into. Read by the azurerm provider and by the naming seed."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "resource_group_name" {
  description = "Existing resource group every resource is placed into. This root does not create it."
  type        = string
}

variable "tags" {
  description = "The tag set every resource carries (context.tags). Merged with the derived tags in locals.tf."
  type        = map(string)
  default     = {}
}

# --- open in the spec: resources.app-service.runtime.container_image (owner: Workload-Team)
variable "container_image" {
  description = "Container image the app runs, as <repository>:<tag> relative to container_registry_url. A tag that is not `latest`, or a digest. OPEN-container-image until the Workload-Team names it."
  type        = string

  validation {
    condition     = !endswith(var.container_image, ":latest")
    error_message = "Pin the image to a tag or digest; `latest` moves under the app without a deployment."
  }
}

variable "container_registry_url" {
  description = "Registry the app pulls container_image from with its managed identity (AcrPull is wiring outside this root), as https://<registry>. https://OPEN-container-registry until the Workload-Team names it."
  type        = string

  validation {
    condition     = startswith(var.container_registry_url, "https://")
    error_message = "container_registry_url is the registry's https URL."
  }
}

# --- open in the spec: resources.foundry.models.model_deployments (owner: Workload-Team)
variable "model_deployments" {
  description = "Model deployments on the AI Foundry account, keyed by deployment name (what the application calls). Model and version are looked up in the region's catalogue as DataZoneStandard, never remembered; OPEN- placeholders until the Workload-Team names them."
  type = map(object({
    model_format  = optional(string, "OpenAI")
    model_name    = string
    model_version = string
  }))
}

# --- the per-stage role assignments of the spec (resources.<resource>.identity.role_assignments)
variable "role_assignments" {
  description = "Who needs which role on which resource, per stage: resource key of the spec => list of { principal (a resource key with a managed identity), role (by name) }."
  type = map(list(object({
    principal = string
    role      = string
  })))

  validation {
    condition = alltrue([
      for resource, entries in var.role_assignments :
      contains(["foundry", "search-service", "storage-account", "key-vault"], resource)
      && alltrue([for e in entries : contains(["app-service", "search-service"], e.principal)])
    ])
    error_message = "role_assignments keys are foundry, search-service, storage-account or key-vault; principals are app-service or search-service (the resources with a system-assigned identity)."
  }
}
