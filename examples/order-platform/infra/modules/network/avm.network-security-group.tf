# Four NSGs (network-security-group__appgw, __apim, __workload, __pe), one module call each.
# decision: network-security-group__appgw.rules.subnet_purpose, __apim, __workload, __pe
# The NSG is created before the subnet that takes its id, so the association is made in the virtual network.
module "nsg" {
  source  = "Azure/avm-res-network-networksecuritygroup/azurerm"
  version = "~> 0.6.0"

  for_each = toset(["appgw", "apim", "workload", "pe"])

  name      = module.naming_nsg[each.key].network_security_group.name
  location  = var.location
  parent_id = var.resource_groups["network"].id

  # default_inbound: the deny is written as a rule, so it shows in the plan. Custom rules are always Allow
  # inbound; the private-endpoint NSG additionally denies Internet outbound (default_outbound: deny_internet).
  security_rules = merge(local.deny_all_inbound, local.nsg_rules[each.key])

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = var.tags
}
