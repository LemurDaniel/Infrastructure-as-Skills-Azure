# Data family, planned alone: `terraform -chdir=modules/data test`.
# The storage module is AzAPI-based: its `resource` output carries the body this family passed in.

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

variables {
  environment   = "development"
  location      = "germanywestcentral"
  workload      = "orders"
  naming_suffix = ["orders", "dev"]
  unique_seed   = "a1b2c3d4"
  tags          = {}
  lock_enabled  = false
  resource_groups = {
    data = {
      name = "rg-orders-dev-data"
      id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-data"
    }
  }
  private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-network/providers/Microsoft.Network/virtualNetworks/vnet-orders-dev/subnets/private-endpoints"
  private_dns_zone_ids = {
    "privatelink.blob.core.windows.net"  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"
    "privatelink.dfs.core.windows.net"   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Network/privateDnsZones/privatelink.dfs.core.windows.net"
    "privatelink.queue.core.windows.net" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev/providers/Microsoft.Network/privateDnsZones/privatelink.queue.core.windows.net"
  }
  diagnostic_workspace_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-orders-dev-observability/providers/Microsoft.OperationalInsights/workspaces/log-orders-dev"
}

run "naming" {
  command = plan

  assert {
    condition     = length(module.storage_datalake.name) <= 24 && startswith(module.storage_datalake.name, "stordersdevdl") && startswith(module.storage_host.name, "stordersdevhost")
    error_message = "Storage account names come from Azure/naming/azurerm: lowercase, no separators, at most 24 characters."
  }
}

run "naming_non_production_stage" {
  command = plan

  variables {
    environment   = "test"
    naming_suffix = ["orders", "tst"]
  }

  assert {
    condition     = startswith(module.storage_datalake.name, "storderststdl")
    error_message = "The test stage carries its own stage code."
  }
}

run "datalake" {
  command = plan

  # decision: storage-account__datalake.storage_kind
  assert {
    condition     = module.storage_datalake.resource.body.kind == "StorageV2" && module.storage_datalake.resource.body.properties.isHnsEnabled == true
    error_message = "A data lake is a StorageV2 account with the hierarchical namespace."
  }

  # decision: storage-account__datalake.data_protection.replication
  assert {
    condition     = module.storage_datalake.resource.body.sku.name == "Standard_LRS"
    error_message = "Locally redundant: three copies in one data centre."
  }

  # decision: storage-account__datalake.data_protection.access_tier
  assert {
    condition     = module.storage_datalake.resource.body.properties.accessTier == "Hot"
    error_message = "Hot: the data is in constant use."
  }

  # not-testable: storage-account__datalake.data_protection.blob_soft_delete_days - set through the module's blob_properties; the blob service is built in a child module whose body no output carries
  # not-testable: storage-account__datalake.data_protection.container_soft_delete_days - set through the module's blob_properties; as above
  # not-testable: storage-account__datalake.data_protection.versioning_enabled - set through the module's blob_properties; as above

  # decision: storage-account__datalake.networking.private_endpoint_subresources
  assert {
    condition     = jsonencode(sort(keys(module.storage_datalake.private_endpoints))) == jsonencode(["blob", "dfs"])
    error_message = "One private endpoint per sub-resource: blob and dfs."
  }
}

run "host" {
  command = plan

  # decision: storage-account__host.data_protection.replication
  assert {
    condition     = module.storage_host.resource.body.sku.name == "Standard_LRS"
    error_message = "Locally redundant: three copies in one data centre."
  }

  # decision: storage-account__host.networking.private_endpoint_subresources
  assert {
    condition     = jsonencode(sort(keys(module.storage_host.private_endpoints))) == jsonencode(["blob", "queue"])
    error_message = "One private endpoint per sub-resource: blob and queue."
  }
}

run "containers" {
  command = plan

  # decision: blob-container.containers.container_names
  assert {
    condition     = jsonencode(keys(module.storage_datalake.containers)) == jsonencode(["telemetry"])
    error_message = "One container on the data lake: telemetry."
  }
}
