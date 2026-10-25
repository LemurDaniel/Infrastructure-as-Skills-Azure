# Rendering an Azure Bastion as Terraform

Mapping from the question set to the Bastion host. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

`Azure/avm-res-network-bastionhost/azurerm` - the primary rendering. Documented against **v0.9.0**
(resolved 2026-10-25); resolve the current version and re-read its README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.9.0`. Status: Available.

**The module is AzAPI-based and constrains `azurerm` to 4.x**: it takes the resource group as
`parent_id` (an id, not a name) and requires `azapi ~> 2.4`, **`azurerm ~> 4.10` - a root calling it
cannot be on 5.x** -, `modtm ~> 0.3`, `random ~> 3.5` and Terraform `>= 1.9, < 2.0`. It creates the
public IP itself, through `Azure/avm-res-network-publicipaddress/azurerm` 0.2.0 (named
`public_ip_address_name`, zones from the Bastion's), so there is no separate public IP call. The root's
provider set is the union.

**Which inputs apply depends on the SKU, and the module validates it:** the `Developer` SKU takes
`virtual_network_id` and no `ip_configuration` and no zones; every other SKU takes `ip_configuration`
and no `virtual_network_id`. A feature switch above `Basic` (copy-paste off, file copy, IP connect,
shareable link) is rejected on `Basic` and `Developer`; session recording and `private_only_enabled`
need `Premium`. The module sends every property regardless of SKU, so an unset switch is written at
its value, not absent.

**The module's defaults agree with the guardrails here** (shareable link, file copy, IP connect and
tunneling all default off) except for the SKU (`Basic`) and the zones (all three); every decision is
still written.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `admin_access` | `private_only_enabled` and `ip_configuration.create_public_ip` | `private_network`: `private_only_enabled = true`, `create_public_ip = false`, no `public_ip_address_id`; Premium |
| `sku` | `sku` | `Developer` / `Basic` / `Standard` / `Premium`; module default `Basic` - written |
| `zone_redundant` | `zones = ["1", "2", "3"]` (a set of strings) or `[]` | Module default all three; `Developer` requires `[]` |
| `scale_units` | `scale_units` | Module default `2`; written |
| `bastion_subnet` | `ip_configuration = { name, subnet_id }` (`Developer`: `virtual_network_id`) | The subnet is named `AzureBastionSubnet` |
| `public_ip_zone_redundant` | follows `zones` | The module creates the address `Standard`, static |
| `shareable_link` | `shareable_link_enabled` | |
| `native_client` | `tunneling_enabled` | Not compatible with session recording |
| `ip_connect` | `ip_connect_enabled` | |
| `file_copy` | `file_copy_enabled` | |
| `copy_paste` | `copy_paste_enabled` | |
| `session_recording` | `session_recording_enabled` | Premium; the module has no input for the recording container |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`, so it is set empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

data "naming_name" "bastion" {
  resource = "Azure::Microsoft.Network/bastionHosts"
}

data "naming_name" "bastion_public_ip" {
  resource = "Azure::Microsoft.Network/publicIPAddresses"
}

module "bastion" {
  source  = "Azure/avm-res-network-bastionhost/azurerm"
  version = "~> 0.9.0"

  name      = data.naming_name.bastion.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: bastion.bastion.sku
  sku = "Standard"
  # decision: bastion.bastion.zone_redundant
  zones = ["1", "2", "3"]
  # decision: bastion.bastion.scale_units
  scale_units = 2

  # decision: bastion.bastion.admin_access, bastion.networking.bastion_subnet
  private_only_enabled = false
  ip_configuration = {
    name                   = "ipconfig-bastion"
    subnet_id              = var.bastion_subnet_id
    create_public_ip       = true
    public_ip_address_name = data.naming_name.bastion_public_ip.name
  }

  # decision: bastion.security.shareable_link
  shareable_link_enabled = false
  # decision: bastion.security.native_client
  tunneling_enabled = false
  # decision: bastion.security.ip_connect
  ip_connect_enabled = false
  # decision: bastion.security.file_copy
  file_copy_enabled = false
  # decision: bastion.security.copy_paste
  copy_paste_enabled = true
  # decision: bastion.security.session_recording
  session_recording_enabled = false

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["BastionAuditLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.bastion.resource_id }
output "dns_name" { value = module.bastion.dns_name }
```

With `admin_access: private_network` the SKU is `Premium`, `private_only_enabled = true` and
`ip_configuration = { name, subnet_id, create_public_ip = false }`. With `sku: Developer` the call
has no `ip_configuration` and no zones: `virtual_network_id = var.virtual_network_id` and `zones = []`.

### Tests

`mock_provider "azapi"`, `"azurerm"` and `"modtm"` keep the plan credential-free. The module's
`resource` output is the `azapi_resource` itself (for a non-Developer SKU `module.bastion.resource` is
the one with `count`, read as the module outputs it), whose `body` is what the root passed in and is
known at plan time: `body.sku.name`, `body.zones`, `body.properties.scaleUnits`, `.enableShareableLink`,
`.enableTunneling`, `.enableIpConnect`, `.enableFileCopy`, `.disableCopyPaste` (inverted),
`.enableSessionRecording` and `.enablePrivateOnlyBastion` are asserted there - exact paths are read off
a first `terraform test` on the pinned version. The diagnostic setting and the public IP module's body
are `# not-testable:` with that reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `sku`, `zone_redundant`, `scale_units` | `azurerm_bastion_host.sku`, `.zones`, `.scale_units` |
| `bastion_subnet` | `azurerm_bastion_host.ip_configuration { name, subnet_id, public_ip_address_id }` (`Developer`: `virtual_network_id`) |
| `admin_access` | `.private_only_enabled`; no public IP resource |
| `shareable_link`, `native_client`, `ip_connect`, `file_copy`, `copy_paste`, `session_recording` | `.shareable_link_enabled`, `.tunneling_enabled`, `.ip_connect_enabled`, `.file_copy_enabled`, `.copy_paste_enabled`, `.session_recording_enabled` |
| public address | `azurerm_public_ip` with `sku = "Standard"`, `allocation_method = "Static"`, `zones` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
