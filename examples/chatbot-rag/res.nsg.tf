# Two groups, one per subnet purpose. The set is keyed by purpose: network-security-group__endpoints
# and network-security-group__integration in the spec.
locals {
  nsgs = {
    endpoints = {
      custom_rules = var.endpoints_nsg_rules

      # rules.subnet_purpose: private_endpoints - baseline from the question set's notes
      baseline_rules = [
        {
          name                       = "allow-vnet-https-inbound"
          priority                   = 100
          direction                  = "Inbound"
          access                     = "Allow"
          protocol                   = "Tcp"
          source_address_prefix      = "VirtualNetwork"
          source_port_range          = "*"
          destination_address_prefix = "VirtualNetwork"
          destination_port_range     = "443"
        },
        # rules.default_inbound: deny_all - written as a rule so it shows in the plan
        {
          name                       = "deny-all-inbound"
          priority                   = 4096
          direction                  = "Inbound"
          access                     = "Deny"
          protocol                   = "*"
          source_address_prefix      = "*"
          source_port_range          = "*"
          destination_address_prefix = "*"
          destination_port_range     = "*"
        },
        # rules.default_outbound: deny_internet - nothing goes out of the endpoint subnet
        {
          name                       = "deny-internet-outbound"
          priority                   = 4096
          direction                  = "Outbound"
          access                     = "Deny"
          protocol                   = "*"
          source_address_prefix      = "*"
          source_port_range          = "*"
          destination_address_prefix = "Internet"
          destination_port_range     = "*"
        },
      ]
    }

    integration = {
      custom_rules = var.integration_nsg_rules

      # rules.subnet_purpose: app_integration - only outbound is used; nothing inbound is needed
      baseline_rules = [
        # rules.default_inbound: deny_all
        {
          name                       = "deny-all-inbound"
          priority                   = 4096
          direction                  = "Inbound"
          access                     = "Deny"
          protocol                   = "*"
          source_address_prefix      = "*"
          source_port_range          = "*"
          destination_address_prefix = "*"
          destination_port_range     = "*"
        },
        # rules.default_outbound: azure_default - no outbound rule is written; the platform
        # defaults apply and the app's dependencies stay reachable.
      ]
    }
  }

  # Keyed "<group>/<rule>", so a rule keeps its address when the list changes.
  nsg_rules = merge([
    for key, nsg in local.nsgs : {
      for r in concat(
        nsg.baseline_rules,
        [for c in nsg.custom_rules : merge(c, { access = "Allow" })]
      ) : "${key}/${r.name}" => merge(r, { nsg = key })
    }
  ]...)
}

# The convention has no <?SUBNAME> in the NSG pattern, so two groups of one workload would get
# the same name. The purpose goes into the name part instead: nsg-we-<stage>-chatrag-endpoints-01.
data "naming_name" "nsg" {
  for_each = local.nsgs

  resource   = "Azure::Microsoft.Network/networkSecurityGroups"
  parameters = { name = "${var.workload}-${each.key}" }
}

resource "azurerm_network_security_group" "this" {
  for_each = local.nsgs

  name                = data.naming_name.nsg[each.key].name
  resource_group_name = var.resource_group_name
  location            = var.location

  # No inline security_rule blocks: the rules are azurerm_network_security_rule resources, and
  # the two fight on every apply.

  tags = local.tags
}

resource "azurerm_network_security_rule" "this" {
  for_each = local.nsg_rules

  name                        = each.value.name
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this[each.value.nsg].name
  priority                    = each.value.priority
  direction                   = each.value.direction
  access                      = each.value.access
  protocol                    = each.value.protocol
  source_address_prefix       = each.value.source_address_prefix
  source_port_range           = each.value.source_port_range
  destination_address_prefix  = each.value.destination_address_prefix
  destination_port_range      = each.value.destination_port_range
}
