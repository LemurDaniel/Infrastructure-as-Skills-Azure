# App family, planned alone: `terraform -chdir=modules/app test`.

mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000000"
      tenant_id       = "00000000-0000-0000-0000-000000000000"
      object_id       = "00000000-0000-0000-0000-000000000000"
      client_id       = "00000000-0000-0000-0000-000000000000"
    }
  }
}
mock_provider "azapi" {}
mock_provider "modtm" {}
mock_provider "random" {}
mock_provider "tls" {}
mock_provider "time" {}

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  resource_groups = {
    main = {
      name = "rg-orders-dev"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev"
    }
    application = {
      name = "rg-orders-dev-application"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-application"
    }
  }
  apim_name = "apim-orders-dev-a1b2"
  subnet_ids = {
    apim                 = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/apim"
    function-integration = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/function-integration"
    private-endpoints    = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/private-endpoints"
    workload             = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/workload"
  }
  private_dns_zone_ids = {
    "privatelink.azurewebsites.net" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Network/privateDnsZones/privatelink.azurewebsites.net"
  }
  diagnostic_workspace_id     = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-observability/providers/Microsoft.OperationalInsights/workspaces/log-orders-dev"
  function_identity_id        = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uai-orders-dev-function"
  function_identity_client_id = "22222222-2222-2222-2222-222222222222"
  host_storage_name           = "stordersdevhosta1b2"
  host_storage_blob_endpoint  = "https://stordersdevhosta1b2.blob.core.windows.net/"
  host_deployment_container   = "app-package"
  publisher_name              = "Contoso"
  publisher_email             = "ops@example.com"
  function_runtime_name       = "node"
  function_runtime_version    = "20"
  vm_size                     = "Standard_D2ds_v5"
  vm_admin_ssh_public_key     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILdvyP4lw/84PbXwja2S+uNDp+NzGXjgm9k1Nof7mQp7 test@example.com"
}

run "naming" {
  command = plan

  assert {
    condition = (
      module.apim.resource.name == "apim-orders-dev-a1b2" &&
      module.function_app.name == "func-orders-dev-a1b2" &&
      module.virtual_machine["1"].name == "vm-orders-dev-1"
    )
    error_message = "Names come from Azure/naming/azurerm; the API Management name is handed over by the root."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
  }

  assert {
    condition     = module.function_app.name == "func-orders-tst-a1b2" && module.virtual_machine["2"].name == "vm-orders-tst-2"
    error_message = "The test stage carries its own stage code."
  }
}

run "api_management" {
  command = plan

  # decision: api-management.service.sku
  assert {
    condition     = module.apim.resource.sku_name == "Developer_1"
    error_message = "Developer, one unit: a test stage without an availability commitment."
  }

  # decision: api-management.access.caller_authentication
  assert {
    condition     = module.apim.products["orders"].subscription_required == true
    error_message = "Callers authenticate with a subscription key: the product requires one."
  }

  # not-testable: api-management.access.rate_limit_calls_per_minute - the policy output carries only its id; the XML with calls="600" is inside azurerm_api_management_policy
  # decision: api-management.access.developer_portal
  assert {
    condition     = module.apim.resource.sign_in[0].enabled == false && module.apim.resource.sign_up[0].enabled == false
    error_message = "No developer portal: sign-in and sign-up are off."
  }

  # decision: api-management.networking.network_integration
  assert {
    condition     = module.apim.resource.virtual_network_type == "Internal" && module.apim.resource.virtual_network_configuration[0].subnet_id == var.subnet_ids["apim"]
    error_message = "Internal: the gateway lives in the apim subnet and has no public address."
  }
}

run "function_app" {
  command = plan

  # decision: function-app.hosting.plan_type
  assert {
    condition     = module.function_app.resource.body.kind == "functionapp,linux" && module.function_app.resource.body.properties.functionAppConfig.deployment.storage.type == "blobcontainer"
    error_message = "Flex Consumption: a Linux function app with a functionAppConfig and a blob deployment container."
  }

  # not-testable: function-app.hosting.zone_redundant - the plan module outputs only its name and id; zoneRedundant sits in the azapi body it builds
  # decision: function-app.hosting.always_ready_instances
  assert {
    condition     = module.function_app.resource.body.properties.functionAppConfig.scaleAndConcurrency.alwaysReady[0].instanceCount == 0
    error_message = "No always-ready instance: scale to zero."
  }

  # decision: function-app.networking.public_network_access
  assert {
    condition = (
      module.function_app.resource.body.properties.publicNetworkAccess == "Enabled" &&
      module.function_app.resource.body.properties.siteConfig.ipSecurityRestrictionsDefaultAction == "Deny" &&
      jsonencode(sort([for r in module.function_app.resource.body.properties.siteConfig.ipSecurityRestrictions : r.ipAddress])) == jsonencode(["ApiManagement", "AzureEventGrid"])
    )
    error_message = "Override: public endpoint on, default deny, only the AzureEventGrid and ApiManagement service tags are allowed."
  }
}

run "virtual_machine" {
  command = plan

  # decision: virtual-machine.instances
  assert {
    condition     = jsonencode(sort(keys(module.virtual_machine))) == jsonencode(["1", "2", "3"])
    error_message = "Three machines (assumed)."
  }

  # decision: virtual-machine.machine.os_type
  assert {
    condition     = module.virtual_machine["1"].resource.disable_password_authentication == true && module.virtual_machine["1"].resource.admin_username == "azureuser"
    error_message = "Linux, key only: only the Linux machine resource has disable_password_authentication."
  }
}
