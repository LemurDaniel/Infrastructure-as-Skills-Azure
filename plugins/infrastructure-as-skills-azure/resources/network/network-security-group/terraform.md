# Rendering a Network Security Group as Terraform

Mapping from the question set to the NSG. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-networksecuritygroup/azurerm` | **v0.6.0** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.6.0`.

**AzAPI only**: it takes `parent_id` (the resource group's id) and requires `azapi ~> 2.12`,
`modtm ~> 0.3`, `random ~> 3.5`, `time ~> 0.13`, Terraform `>= 1.11`; no `azurerm`. The root's
provider set is the union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `subnet_purpose` | the name `nsg-<purpose>`, and the baseline rules | See `notes.md` |
| `default_inbound` | `security_rules` entry: Deny, Inbound, any to any, priority 4096 | Written as a rule |
| `default_outbound` | `security_rules` entry: Deny, Outbound, destination `Internet`, priority 4096 | Only for `deny_internet` |
| `rules` | `security_rules = { <k> = { name, priority, direction, access = "Allow", protocol, source_*, destination_* } }` | The module's map key is arbitrary; names unique |
| `diagnostic_*` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = [] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories, or every log is collected beside them; no metrics for an NSG |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "nsg" {
  source  = "Azure/avm-res-network-networksecuritygroup/azurerm"
  version = "~> 0.6.0"

  name      = data.naming_name.nsg.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  security_rules = merge(
    {
      # decision: network-security-group.rules.default_inbound - explicit, so it shows in the plan
      deny_all_inbound = {
        name                       = "deny-all-inbound"
        priority                   = 4096
        direction                  = "Inbound"
        access                     = "Deny"
        protocol                   = "*"
        source_address_prefix      = "*"
        source_port_range          = "*"
        destination_address_prefix = "*"
        destination_port_range     = "*"
      }
    },
    local.baseline_rules,  # by subnet_purpose
    local.explicit_rules,  # from `rules`, always Allow
  )

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"]
      log_groups            = []
      metric_categories     = []
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.nsg.resource_id }
```

The member names of `security_rules` and `diagnostic_settings` are read from the README of the
pinned version. The module's output `resource_id` is what the virtual-network set takes for a
subnet's `network_security_group`.

### Tests

With `azapi` and `modtm` mocked, the module's `resource` output is the NSG's `azapi_resource`,
so asserts target `body.properties.securityRules` at plan time: the deny rule at 4096, every
custom rule `Allow`, priorities unique, no inbound allow from `*` or `Internet`. The
diagnostic setting is `# not-testable:` where the plan hides it. The paths are read off a first
`terraform test` run on the pinned version.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource |
|---|---|
| the NSG | `azurerm_network_security_group` |
| `rules` and the defaults | `azurerm_network_security_rule` **or** inline `security_rule` blocks - **not both**, the two fight on every apply |
| the association | `azurerm_subnet_network_security_group_association` - or the subnet's own argument; one of them, never both |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
