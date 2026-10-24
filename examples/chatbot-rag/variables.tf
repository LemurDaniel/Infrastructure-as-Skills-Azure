# Context: no defaults, every value comes from environments/<stage>.tfvars.

variable "subscription_id" {
  description = "Subscription of the stage (stage_isolation: subscription). Open in the spec: context.subscription_id."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "resource_group_name" {
  description = "Existing resource group of the stage; this deployment does not create it. Open in the spec: context.resource_group_name."
  type        = string
}

variable "location" {
  description = "Azure region. Also drives the location code in rendered names."
  type        = string
}

variable "workload" {
  description = "Workload short name, rendered into every name. Storage account names are the tightest: st + location code + stage code + workload + 01 must fit 24 characters."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{2,14}$", var.workload))
    error_message = "workload must be 2-14 lowercase letters or digits."
  }
}

variable "environment" {
  description = "Stage. Drives the rendered name and the per-stage values."
  type        = string

  validation {
    # The keys of mappings.environment in naming.yaml that this deployment uses.
    condition     = contains(["development", "test", "production"], var.environment)
    error_message = "environment must be one of development, test, production."
  }
}

variable "tags" {
  description = "Tag set applied to every resource. Open in the spec: context.tags."
  type        = map(string)
}

# Network ----------------------------------------------------------------------------------------

variable "address_space" {
  description = "Address range of the stage's new virtual network. Open in the spec: deployment.address_space."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.address_space))
    error_message = "address_space must be a CIDR range."
  }
}

variable "subnets" {
  description = "Prefixes of the subnets, keyed by subnet name. snet-endpoints holds the private endpoints, snet-web the App Service integration (delegated to Microsoft.Web/serverFarms). Open in the spec: resources.virtual-network.addressing.subnets and deployment.private_endpoint_subnet_prefix."
  type = map(object({
    prefix = string
  }))

  validation {
    condition     = alltrue([for s in ["snet-endpoints", "snet-web"] : contains(keys(var.subnets), s)]) && alltrue([for s in var.subnets : can(cidrnetmask(s.prefix))])
    error_message = "subnets needs snet-endpoints and snet-web, each with a CIDR prefix."
  }
}

variable "dns_servers" {
  description = "Custom DNS servers of the virtual network. Empty: Azure-provided DNS, which resolves the privatelink zones linked to the network."
  type        = list(string)
}

variable "subnets_expecting_nsg" {
  description = "Subnets that carry a network security group: snet-endpoints gets the endpoints group, snet-web the integration group."
  type        = list(string)

  validation {
    condition     = alltrue([for s in var.subnets_expecting_nsg : contains(["snet-endpoints", "snet-web"], s)])
    error_message = "Only snet-endpoints and snet-web have a security group."
  }
}

variable "private_endpoint_subnets" {
  description = "Subnet name of each resource's private endpoint, a key of var.subnets."
  type = object({
    key_vault       = string
    storage_account = string
    foundry         = string
    search_service  = string
    app_service     = string
  })
}

variable "app_integration_subnet" {
  description = "Subnet name of the App Service VNet integration, a key of var.subnets."
  type        = string
}

variable "endpoints_nsg_rules" {
  description = "Explicit allow rules of the endpoints group, in addition to the baseline. Always Allow; priority 100-4095, unique; never * or Internet as the source of an inbound allow."
  type = list(object({
    name                       = string
    priority                   = number
    direction                  = string
    protocol                   = string
    source_address_prefix      = string
    source_port_range          = optional(string, "*")
    destination_address_prefix = string
    destination_port_range     = string
  }))
}

variable "integration_nsg_rules" {
  description = "Explicit allow rules of the integration group, in addition to the baseline. Same shape as endpoints_nsg_rules."
  type = list(object({
    name                       = string
    priority                   = number
    direction                  = string
    protocol                   = string
    source_address_prefix      = string
    source_port_range          = optional(string, "*")
    destination_address_prefix = string
    destination_port_range     = string
  }))
}

# Identity ---------------------------------------------------------------------------------------

variable "role_assignments" {
  description = "Role assignments between the deployment's resources. resource is the scope (application-insights, key-vault, storage-account, foundry, search-service); principal is the system-assigned identity of app-service or search-service."
  type = list(object({
    resource  = string
    principal = string
    role      = string
  }))

  validation {
    condition = alltrue([
      for ra in var.role_assignments :
      contains(["application-insights", "key-vault", "storage-account", "foundry", "search-service"], ra.resource) &&
      contains(["app-service", "search-service"], ra.principal)
    ])
    error_message = "resource must be one of application-insights, key-vault, storage-account, foundry, search-service; principal one of app-service, search-service."
  }
}

# Per-stage cost knobs ---------------------------------------------------------------------------

variable "search_sku" {
  description = "SKU of the search service (basic outside production, standard in production)."
  type        = string

  validation {
    condition     = contains(["free", "basic", "standard", "standard2", "standard3", "storage_optimized_l1", "storage_optimized_l2"], var.search_sku)
    error_message = "search_sku must be an Azure AI Search SKU."
  }
}

variable "app_service_sku" {
  description = "SKU of the App Service plan (B1 outside production, P1v3 in production)."
  type        = string
}

# Open values --------------------------------------------------------------------------------------

variable "model_deployments" {
  description = "Model deployments of the Foundry account, keyed by deployment name. Open in the spec: resources.foundry.models.model_deployments (chat and embedding model; regional, with quota - looked up at render time, never recalled). format is the model provider's format, OpenAI for the Azure OpenAI models."
  type = map(object({
    format  = optional(string, "OpenAI")
    name    = string
    version = string
  }))
}

variable "runtime_stack" {
  description = "Runtime of the web app: dotnet, go, java, node, php or python. Open in the spec: resources.app-service.runtime.runtime_stack."
  type        = string

  validation {
    condition     = contains(["dotnet", "go", "java", "node", "php", "python"], var.runtime_stack)
    error_message = "runtime_stack must be one of dotnet, go, java, node, php, python."
  }
}

variable "runtime_version" {
  description = "Version of the runtime in the notation of azurerm_linux_web_app.site_config.application_stack (for example 20-lts for node). Open in the spec: resources.app-service.runtime.runtime_version."
  type        = string
}
