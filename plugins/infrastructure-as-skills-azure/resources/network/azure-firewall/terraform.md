# Rendering an Azure Firewall as Terraform

Mapping from the question set to the firewall, its policy and its public addresses. General
layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM modules

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-azurefirewall/azurerm` | **v0.3.0** | 2026-10-25 | Available |
| `Azure/avm-res-network-firewallpolicy/azurerm` | **v0.3.4** | 2026-10-25 | Available |
| `Azure/avm-res-network-publicipaddress/azurerm` | **v0.2.1** | 2026-10-25 | Available |

Resolve the current versions and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pins are `~> 0.3.0`, `~> 0.3.4` and
`~> 0.2.1`. The firewall policy repository carries one stray tag, `v.0.3.3`: a sort of the tag list by
version puts it wrongly, read the highest `v0.3.x`.

**The firewall and the policy modules are `azurerm`-based**: they take `resource_group_name` (a name,
not an id) and require `azurerm >= 3.71, < 5.0.0` - **a root calling them cannot be on 5.x** - plus
`modtm ~> 0.3` and `random ~> 3.5`; the policy module also needs `azapi ~> 2.4`, the public IP module
`azapi ~> 2.4` and `azurerm >= 3.116, < 5.0`. The firewall module wants Terraform `~> 1.7`, the policy
module `~> 1.5`; the root's own floor is the highest of its modules. The root's provider set is the union.

**The firewall module creates no public IP and no policy.** Both are separate modules, referenced by
id: `firewall_policy_id` and, in `firewall_ip_configuration`, `public_ip_address_id`. The policy
carries every setting that Azure keeps on the policy and not on the firewall: DNS proxy, SNAT ranges,
threat intelligence, intrusion detection, TLS inspection. Rule collection groups are the policy
module's submodule `modules/rule_collection_groups` - wiring, not rendered here.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku_tier` | firewall `firewall_sku_tier` and policy `firewall_policy_sku` | `Basic` / `Standard` / `Premium`, the same on both; `firewall_sku_name = "AZFW_VNet"` is required and fixed |
| `zone_redundant` | firewall `firewall_zones`; public IP module `zones` | `["1", "2", "3"]` or `[]`; the module defaults to all three. The public IP module takes `set(number)` |
| `firewall_subnet` | firewall `firewall_ip_configuration = [{ name, subnet_id, public_ip_address_id }]` | Only the first entry carries the subnet; the others carry just an address |
| `public_ip_count` | one public IP module call per address, one `firewall_ip_configuration` entry each | `allocation_method = "Static"`, `sku = "Standard"` |
| `forced_tunneling`, `management_subnet` | firewall `firewall_management_ip_configuration = { name, subnet_id, public_ip_address_id }` | An object, not a list; its own public IP, same zones |
| `dns_proxy`, `dns_servers` | policy `firewall_policy_dns = { proxy_enabled, servers }` | `servers = null` for Azure-provided DNS |
| `snat_private_ranges` | policy `firewall_policy_private_ip_ranges` | A list; `IANAPrivateRanges` is the special value. The firewall module has its own `firewall_private_ip_ranges`, which applies when no policy is attached - unused |
| `threat_intelligence_mode` | policy `firewall_policy_threat_intelligence_mode` | `Off` / `Alert` / `Deny`; module default unset - written |
| `idps_mode` | policy `firewall_policy_intrusion_detection = { mode }` | Premium only; `null` otherwise |
| `tls_inspection`, `tls_certificate_secret_id` | policy `firewall_policy_tls_certificate = { name, key_vault_secret_id }` | Premium only |
| `policy_identity`, `user_assigned_identity_ids` | policy `firewall_policy_identity = { type = "UserAssigned", identity_ids }` | `null` for none |
| `rule_collection_groups` | policy submodule `modules/rule_collection_groups` | Wiring: filled by the pattern or the platform |
| `diagnostic_*`, `metrics_enabled` | firewall `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"], log_analytics_destination_type = "Dedicated" } }` | `log_groups` defaults to `["allLogs"]`, so it is set empty beside the categories |
| `deployment.module_telemetry` | `enable_telemetry` | On every module |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "naming_name" "azure_firewall" {
  resource = "Azure::Microsoft.Network/azureFirewalls"
}

data "naming_name" "firewall_policy" {
  resource = "Azure::Microsoft.Network/firewallPolicies"
}

data "naming_name" "firewall_public_ip" {
  resource = "Azure::Microsoft.Network/publicIPAddresses"
  index    = { count = var.public_ip_count + 1 } # the last one is the management address
}

module "firewall_policy" {
  source  = "Azure/avm-res-network-firewallpolicy/azurerm"
  version = "~> 0.3.4"

  name                = data.naming_name.firewall_policy.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: azure-firewall.firewall.sku_tier
  firewall_policy_sku = "Standard"

  # decision: azure-firewall.networking.dns_proxy, dns_servers
  firewall_policy_dns = {
    proxy_enabled = true
    servers       = null # Azure-provided DNS
  }
  # decision: azure-firewall.networking.snat_private_ranges
  firewall_policy_private_ip_ranges = ["IANAPrivateRanges"]

  # decision: azure-firewall.security.threat_intelligence_mode
  firewall_policy_threat_intelligence_mode = "Deny"
  # decision: azure-firewall.security.idps_mode - Premium only
  firewall_policy_intrusion_detection = null

  enable_telemetry = true
  tags             = local.tags
}

module "firewall_public_ip" {
  source  = "Azure/avm-res-network-publicipaddress/azurerm"
  version = "~> 0.2.1"
  count   = var.public_ip_count

  name                = data.naming_name.firewall_public_ip.at_index[count.index]
  location            = var.location
  resource_group_name = var.resource_group_name

  allocation_method = "Static"
  sku               = "Standard"
  # decision: azure-firewall.firewall.zone_redundant
  zones = [1, 2, 3]

  enable_telemetry = true
  tags             = local.tags
}

module "firewall" {
  source  = "Azure/avm-res-network-azurefirewall/azurerm"
  version = "~> 0.3.0"

  name                = data.naming_name.azure_firewall.name
  location            = var.location
  resource_group_name = var.resource_group_name

  firewall_sku_name = "AZFW_VNet"
  # decision: azure-firewall.firewall.sku_tier
  firewall_sku_tier  = "Standard"
  firewall_policy_id = module.firewall_policy.resource_id
  # decision: azure-firewall.firewall.zone_redundant
  firewall_zones = ["1", "2", "3"]

  # decision: azure-firewall.firewall.firewall_subnet, public_ip_count
  firewall_ip_configuration = [
    for i, pip in module.firewall_public_ip : {
      name                 = "ipconfig-${i + 1}"
      public_ip_address_id = pip.resource_id
      subnet_id            = i == 0 ? var.firewall_subnet_id : null
    }
  ]

  # decision: azure-firewall.networking.forced_tunneling, management_subnet - only when forced
  firewall_management_ip_configuration = null

  diagnostic_settings = {
    workspace = {
      workspace_resource_id          = var.diagnostic_workspace_id
      log_categories                 = ["AZFWNetworkRule", "AZFWApplicationRule", "AZFWNatRule", "AZFWThreatIntel", "AZFWDnsQuery", "AZFWFqdnResolveFailure"]
      log_groups                     = []
      metric_categories              = ["AllMetrics"]
      log_analytics_destination_type = "Dedicated"
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.firewall.resource_id }
output "policy_id" { value = module.firewall_policy.resource_id }
```

With `forced_tunneling: true` (and always on `Basic`) the last address is the management one and the
module gets its object:

```hcl
  firewall_management_ip_configuration = {
    name                 = "mgmt"
    public_ip_address_id = module.firewall_public_ip[var.public_ip_count].resource_id
    subnet_id            = var.management_subnet_id
  }
```

with the public IP module's `count` raised by one and the `for` over the addresses sliced to
`slice(module.firewall_public_ip, 0, var.public_ip_count)`, so that the management address does not
become a data-plane one. With `tls_inspection: true` the policy module gets
`firewall_policy_tls_certificate = { name, key_vault_secret_id }` and
`firewall_policy_identity = { type = "UserAssigned", identity_ids = var.user_assigned_identity_ids }`.
The first address carries the subnet; one that does not is rejected by Azure, so the list is never
reordered.

### Tests

`mock_provider "azurerm"`, `"azapi"` and `"modtm"` keep the plan credential-free. Both modules are
`azurerm`-based, so their `resource` output is the `azurerm` resource, echoed from the inputs: the
firewall's `zones`, `sku_tier`, `sku_name` and `firewall_policy_id` are asserted on
`module.firewall.resource`, the policy's `sku`, `threat_intelligence_mode`, `dns[0].proxy_enabled` and
`private_ip_ranges` on `module.firewall_policy.resource` (exact paths are read off a first
`terraform test` on the pinned versions). The diagnostic setting is a child resource of the module and
its categories are `# not-testable:` with that reason; the rule collection groups are the pattern's and
tested there.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `sku_tier`, `zone_redundant` | `azurerm_firewall.sku_name = "AZFW_VNet"`, `.sku_tier`, `.zones`; `azurerm_firewall_policy.sku` |
| `firewall_subnet`, `public_ip_count` | `azurerm_firewall.ip_configuration { name, subnet_id, public_ip_address_id }` - the subnet on the first block only; `azurerm_public_ip` with `sku = "Standard"`, `allocation_method = "Static"`, `zones` |
| `forced_tunneling` | `azurerm_firewall.management_ip_configuration { name, subnet_id, public_ip_address_id }` |
| `dns_proxy`, `dns_servers` | `azurerm_firewall_policy.dns { proxy_enabled, servers }` |
| `snat_private_ranges` | `azurerm_firewall_policy.private_ip_ranges` |
| `threat_intelligence_mode` | `azurerm_firewall_policy.threat_intelligence_mode` |
| `idps_mode` | `azurerm_firewall_policy.intrusion_detection { mode }` |
| `tls_inspection` | `azurerm_firewall_policy.tls_certificate { name, key_vault_secret_id }` and `.identity` |
| `rule_collection_groups` | `azurerm_firewall_policy_rule_collection_group` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` and `log_analytics_destination_type = "Dedicated"` |
