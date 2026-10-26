# Front Door Premium: the only public surface (deployment.network_exposure exceptions: front-door).
# The firewall policy and the security policy that binds it live inside this module.
module "front_door" {
  source  = "Azure/avm-res-cdn-profile/azurerm"
  version = "~> 0.1.9"

  name                = module.naming.cdn_frontdoor_profile.name
  location            = "global" # a Front Door profile is global, whatever context.location says
  resource_group_name = var.resource_groups["network"].name

  # decision: front-door.profile.sku
  sku                      = "Premium_AzureFrontDoor"
  response_timeout_seconds = 60

  front_door_endpoints = {
    default = {
      name = module.naming.cdn_frontdoor_endpoint.name_unique
    }
  }

  front_door_origin_groups = {
    appgw = {
      name = "appgw"
      health_probe = {
        default = {
          interval_in_seconds = 100
          path                = "/"
          protocol            = "Http"
          request_type        = "HEAD"
        }
      }
      load_balancing = {
        default = {}
      }
    }
  }

  # decision: front-door.delivery.origin_connection
  # OVERRIDE (default: private_link): the origin is the Application Gateway, which Front Door cannot reach
  # over Private Link. The origin is its public address; the gateway only admits Front Door.
  front_door_origins = {
    appgw = {
      name                           = "appgw"
      origin_group_key               = "appgw"
      host_name                      = module.public_ip_appgw.public_ip_address
      certificate_name_check_enabled = "false" # the origin is addressed by IP
      http_port                      = 80
      https_port                     = 443
      priority                       = 1
      weight                         = 500
    }
  }

  front_door_routes = {
    default = {
      name             = "default"
      origin_group_key = "appgw"
      origin_keys      = ["appgw"]
      endpoint_key     = "default"
      # OPEN (Application Gateway listeners): HttpOnly while the gateway has only the scaffold HTTP listener;
      # HttpsOnly once a certificate is bound.
      forwarding_protocol    = "HttpOnly"
      supported_protocols    = ["Http", "Https"]
      patterns_to_match      = ["/*"]
      https_redirect_enabled = true
      link_to_default_domain = true

      # decision: front-door.delivery.caching
      cache = {
        default = {
          query_string_caching_behavior = "IgnoreQueryString"
          compression_enabled           = true
          content_types_to_compress     = ["application/json", "text/html", "text/css", "text/javascript", "text/plain"]
        }
      }
    }
  }

  front_door_firewall_policies = {
    waf = {
      name     = replace(module.naming.frontdoor_firewall_policy.name, "-", "") # alphanumeric only
      sku_name = "Premium_AzureFrontDoor"
      enabled  = true # decision: front-door.security.waf_enabled
      # decision: front-door.security.waf_mode
      mode                = "Prevention"
      resource_group_name = var.resource_groups["network"].name

      managed_rules = {
        default = {
          type    = "Microsoft_DefaultRuleSet"
          version = "2.1"
          action  = "Block"
        }
        bots = {
          type    = "Microsoft_BotManagerRuleSet"
          version = "1.1"
          action  = "Block"
        }
      }
    }
  }

  front_door_security_policies = {
    waf = {
      name = "waf"
      firewall = {
        front_door_firewall_policy_key = "waf"
        association = {
          endpoint_keys     = ["default"]
          patterns_to_match = ["/*"]
        }
      }
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}

# The module does not export the profile's id (the GUID in the X-Azure-FDID header), so it is read back.
data "azapi_resource" "front_door" {
  type                   = "Microsoft.Cdn/profiles@2023-07-01-preview"
  resource_id            = module.front_door.resource_id
  response_export_values = ["properties.frontDoorId"]
}
