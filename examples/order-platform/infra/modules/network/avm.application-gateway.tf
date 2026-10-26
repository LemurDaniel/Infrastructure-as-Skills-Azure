# Application Gateway v2 with a WAF policy. The firewall is a separate module and resource; the gateway references it by id.

module "waf_policy_appgw" {
  source  = "Azure/avm-res-network-applicationgatewaywebapplicationfirewallpolicy/azurerm"
  version = "~> 0.2.0"

  name                = module.naming_appgw.web_application_firewall_policy.name
  location            = var.location
  resource_group_name = var.resource_groups["network"].name

  # decision: application-gateway.gateway.waf_mode - Prevention blocks; Detection only records.
  policy_settings = {
    enabled                  = true
    mode                     = "Prevention"
    request_body_check       = true
    request_body_enforcement = true
  }

  managed_rules = {
    managed_rule_set = {
      owasp = {
        type    = "OWASP"
        version = "3.2"
      }
    }
  }

  # Front Door is the only caller: a request without Front Door's profile id in X-Azure-FDID is blocked.
  # The NSG admits the AzureFrontDoor.Backend tag, but that tag is shared by every Front Door profile.
  custom_rules = {
    front_door_only = {
      name      = "FrontDoorOnly"
      priority  = 10
      rule_type = "MatchRule"
      action    = "Block"
      enabled   = true
      match_conditions = {
        header_is_not_ours = {
          operator           = "Equal"
          negation_condition = true
          match_values       = [data.azapi_resource.front_door.output.properties.frontDoorId]
          match_variables = [{
            variable_name = "RequestHeaders"
            selector      = "X-Azure-FDID"
          }]
        }
      }
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}

module "application_gateway" {
  source  = "Azure/avm-res-network-applicationgateway/azurerm"
  version = "~> 0.5.3"

  name      = module.naming_appgw.application_gateway.name
  location  = var.location
  parent_id = var.resource_groups["network"].id

  # decision: application-gateway.gateway.waf_enabled
  sku = {
    name = "WAF_v2"
    tier = "WAF_v2"
  }
  firewall_policy = { id = module.waf_policy_appgw.resource_id }

  # decision: application-gateway.gateway.capacity_min - outage_impact tolerable: one instance is enough
  autoscale_configuration = {
    min_capacity = 1
    max_capacity = 5
  }
  # decision: application-gateway.gateway.zone_redundant
  zones = null

  gateway_ip_configurations = [{
    name = "gateway-ip"
    properties = {
      subnet = { id = module.virtual_network.subnets["appgw"].resource_id }
    }
  }]

  # decision: application-gateway.networking.frontend_exposure
  # OVERRIDE (default: private): Front Door Premium cannot reach an Application Gateway through Private Link,
  # so the gateway keeps a public IP. It admits only the AzureFrontDoor.Backend service tag (NSG) and requests
  # that carry Front Door's id header (WAF custom rule FrontDoorOnly).
  frontend_ip_configurations = [{
    name = "public"
    properties = {
      public_ip_address = { id = module.public_ip_appgw.resource_id }
    }
  }]

  managed_identities = {
    user_assigned_resource_ids = [var.appgw_identity_id]
  }

  ssl_policy = {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101S"
  }
  enable_http2 = true

  # decision: application-gateway.networking.listeners
  # OPEN (domains and TLS certificates): the spec's list is empty, so a scaffold listener on port 80 stands in.
  # It routes to API Management. Replace it with HTTPS listeners and certificates when the open entry is answered.
  frontend_ports = [{
    name       = "port-80"
    properties = { port = 80 }
  }]

  http_listeners = [{
    name = "scaffold-http"
    properties = {
      frontend_ip_configuration = { id = "${local.appgw_id}/frontendIPConfigurations/public" }
      frontend_port             = { id = "${local.appgw_id}/frontendPorts/port-80" }
      protocol                  = "Http"
      host_names                = var.appgw_listener_hostnames
    }
  }]

  backend_address_pools = [{
    name = "apim"
    properties = {
      backend_addresses = [{ fqdn = var.appgw_backend_hostname }]
    }
  }]

  probes = [{
    name = "apim-status"
    properties = {
      protocol                                  = "Https"
      path                                      = "/status-0123456789abcdef"
      interval                                  = 30
      timeout                                   = 30
      unhealthy_threshold                       = 3
      pick_host_name_from_backend_http_settings = true
      match                                     = { status_codes = ["200-399"] }
    }
  }]

  backend_http_settings_collection = [{
    name = "apim-https"
    properties = {
      port                                = 443
      protocol                            = "Https"
      cookie_based_affinity               = "Disabled"
      request_timeout                     = 30
      pick_host_name_from_backend_address = true
      probe                               = { id = "${local.appgw_id}/probes/apim-status" }
    }
  }]

  request_routing_rules = [{
    name = "scaffold-to-apim"
    properties = {
      rule_type             = "Basic"
      priority              = 100
      http_listener         = { id = "${local.appgw_id}/httpListeners/scaffold-http" }
      backend_address_pool  = { id = "${local.appgw_id}/backendAddressPools/apim" }
      backend_http_settings = { id = "${local.appgw_id}/backendHttpSettingsCollection/apim-https" }
    }
  }]

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
