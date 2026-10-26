# Two identities in the main resource group (identities are not in the table of a split role):
# user-assigned-identity__function (host storage, Service Bus, deployment package) and
# user-assigned-identity__appgw (the gateway's identity for certificates later).
# The question set carries no decisions beyond the purpose, which becomes the name part and a tag.
module "naming" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(["function", "appgw"])

  suffix        = concat(var.naming_suffix, [each.key])
  unique-seed   = var.unique_seed
  unique-length = 4
}

module "identity" {
  source  = "Azure/avm-res-managedidentity-userassignedidentity/azurerm"
  version = "~> 0.5.3"

  for_each = toset(["function", "appgw"])

  name                = module.naming[each.key].user_assigned_identity.name
  location            = var.location
  resource_group_name = var.resource_groups["main"].name

  # isolation_scope None is unset; no federated credentials (the pipeline's identity is not rendered here).
  isolation_scope                = null
  federated_identity_credentials = {}

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = merge(var.tags, { purpose = each.key })
}
