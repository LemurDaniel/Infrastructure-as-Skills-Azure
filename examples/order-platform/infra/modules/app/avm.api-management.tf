locals {
  # Service-level policy. rate_limit_calls_per_minute: 600, counted per caller address.
  # caller_authentication subscription_key: the key itself is required by the product below
  # (subscription_required = true); the gateway policy only throttles.
  apim_global_policy = <<-XML
    <policies>
      <inbound>
        <base />
        <rate-limit-by-key calls="600" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
      </inbound>
      <backend><base /></backend>
      <outbound><base /></outbound>
      <on-error><base /></on-error>
    </policies>
  XML
}

module "apim" {
  source  = "Azure/avm-res-apimanagement-service/azurerm"
  version = "~> 0.9.0"

  name                = var.apim_name
  location            = var.location
  resource_group_name = var.resource_groups["application"].name

  # OPEN (publisher name and e-mail): the module default is a placeholder, so both are always written.
  publisher_name  = var.publisher_name
  publisher_email = var.publisher_email

  # decision: api-management.service.sku - Developer: a test stage without an availability commitment
  sku_name = "Developer_1"
  zones    = null

  # decision: api-management.networking.network_integration - internal: the gateway has no public address
  virtual_network_type      = "Internal"
  virtual_network_subnet_id = var.subnet_ids["apim"]
  # Management plane only; a VNet-injected instance cannot switch it off. The data plane is private.
  public_network_access_enabled = true

  security = {
    enable_frontend_ssl30 = false
    enable_frontend_tls10 = false
    enable_frontend_tls11 = false
    enable_backend_ssl30  = false
    enable_backend_tls10  = false
    enable_backend_tls11  = false
  }
  client_certificate_enabled = false

  # decision: api-management.access.rate_limit_calls_per_minute
  policy = {
    xml_content = local.apim_global_policy
  }

  # decision: api-management.access.caller_authentication - subscription_key
  # (local_auth exception of the deployment: API Management keeps keys)
  products = {
    orders = {
      display_name          = "orders"
      description           = "Order API"
      subscription_required = true
      approval_required     = false
      state                 = "published"
    }
  }

  # decision: api-management.access.developer_portal - false: sign-in and sign-up off
  sign_in = { enabled = false }
  sign_up = {
    enabled = false
    terms_of_service = {
      consent_required = false
      enabled          = false
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["GatewayLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
