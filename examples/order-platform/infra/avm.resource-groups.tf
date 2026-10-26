# Resource groups: main plus network/data/application/observability, all created
# (deployment.resource_group_split, resource_group_mode_<role>: create).
# A created group carries CanNotDelete in the stages that deployment.resource_group_lock names (production).

module "naming_resource_group" {
  source  = "Azure/naming/azurerm"
  version = "~> 0.4.4"

  for_each = toset(local.resource_group_roles)

  suffix        = each.key == "main" ? local.naming_suffix : concat(local.naming_suffix, [each.key])
  unique-seed   = local.unique_seed
  unique-length = 4
}

module "resource_group" {
  source  = "Azure/avm-res-resources-resourcegroup/azurerm"
  version = "~> 0.4.0"

  for_each = toset(local.resource_group_roles)

  name     = module.naming_resource_group[each.key].resource_group.name
  location = var.location

  # decision: deployment.resource_group_lock
  lock = var.lock_enabled ? { kind = "CanNotDelete" } : null

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}

locals {
  resource_groups = {
    for role, rg in module.resource_group : role => {
      name = rg.name
      id   = rg.resource_id
    }
  }
}
