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

What each decision renders to - the input and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Input | Note |
|---|---|---|
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

What each decision renders to - the argument and the literal of every answer - is in
[render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Resource |
|---|---|
| the NSG | `azurerm_network_security_group` |
| the association | `azurerm_subnet_network_security_group_association` - or the subnet's own argument; one of them, never both |
