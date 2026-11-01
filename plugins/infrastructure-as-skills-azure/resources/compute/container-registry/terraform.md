# Rendering a Container Registry as Terraform

Mapping from the question set to the registry. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-containerregistry-registry/azurerm` | **v0.8.0** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.8.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm >= 4.81.0, < 5.0.0` -
**a root calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random`, and
Terraform `>= 1.8`. The root's provider set is the union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "registry" {
  source  = "Azure/avm-res-containerregistry-registry/azurerm"
  version = "~> 0.8.0"

  name                = data.naming_name.registry.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: container-registry.registry.sku
  sku = "Premium"
  # decision: container-registry.registry.zone_redundant - fixed at creation
  zone_redundancy_enabled = true
  georeplications         = []
  # decision: container-registry.registry.retention_untagged_days - Bicep's default is 15
  retention_policy_in_days = 7

  # decision: container-registry.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  network_rule_bypass_option    = "None"
  export_policy_enabled         = false
  # not-testable: container-registry.networking.image_push_path - the image pipeline's steps, not a registry argument
  private_endpoints = {
    registry = {
      name               = data.naming_name.registry_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: container-registry.security.admin_enabled - inverse of local_auth
  admin_enabled          = false
  anonymous_pull_enabled = false

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["ContainerRegistryRepositoryEvents", "ContainerRegistryLoginEvents"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.registry.resource_id }
output "login_server" { value = module.registry.login_server }
```

Output names and the member names of `network_rule_set` and `diagnostic_settings` are read from
the README of the pinned version.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's resources: the SKU,
zone redundancy, the public flag, the admin flag, the export policy, the retention. The output
paths are read off a first `terraform test` run on the pinned version. What the module builds
in child resources - the endpoint, the diagnostic setting, role assignments - is marked
`# not-testable:` with a reason where the plan hides it.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
