# Rendering a Static Web App as Terraform

Mapping from the question set to the app. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-web-staticsite/azurerm` | **v0.6.2** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.6.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0, < 5.0` -
**a root calling it cannot be on 5.x** - plus `azapi ~> 2.0`, `modtm ~> 0.3`, `random`, and
Terraform `>= 1.7`. The root's provider set is the union with the other modules. Validated with
`terraform validate` against v0.6.2.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide and other inputs

| Setting | Input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy`; under `deployment` the zone ids go into `private_dns_zone_resource_ids` once the zone exists |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |
| (no diagnostics) | none | The module has no `diagnostic_settings` input; see the notes |

### The call

```hcl
module "static_web_app" {
  source  = "Azure/avm-res-web-staticsite/azurerm"
  version = "~> 0.6.0"

  name                = data.naming_name.static_web_app.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: static-web-app.static_web_app.sku
  sku_tier = "Standard"
  sku_size = "Standard"
  # decision: static-web-app.static_web_app.preview_environments_enabled - the module default is true
  preview_environments_enabled = false

  # decision: static-web-app.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  private_endpoints = {
    staticsite = {
      name               = data.naming_name.static_web_app_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities = { system_assigned = false, user_assigned_resource_ids = [var.user_assigned_identity_id] }
  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.static_web_app.resource_id }
output "default_host_name" { value = module.static_web_app.resource_uri }
```

The member names of `private_endpoints` and the output names are read from the README of the
pinned version. The module also exports `api_key` (sensitive): do not wire it anywhere.

### Tests

With `azurerm` mocked, the module's `resource` output is the `azurerm_static_web_app`, so asserts
target its attributes at plan time: `sku_tier`, `sku_size`, `public_network_access_enabled`,
`preview_environments_enabled` and `identity`. The exact paths are read off a first `terraform
test` run on the pinned version. What the module builds in child resources - the private
endpoint and the role assignments - is `# not-testable:` with a reason where the plan hides it.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; checked against `terraform providers schema -json`
(azurerm 5.11.0).

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
