# Rendering Container Instances as Terraform

Mapping from the question set to the container group. General layout, variables and tagging are
in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-containerinstance-containergroup/azurerm` | **v0.2.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm ~> 4.0` - **a root
calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random ~> 3.5`, and Terraform
`~> 1.5`. The root's provider set is the union with the other modules. It is a **thin** module: one
`azurerm_container_group`, no diagnostic settings, no lock, and a `private_endpoints` input for a
feature the service does not have. Validated with `terraform validate` against v0.2.0.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide and fixed inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| (OS) | `os_type = "Linux"` | Required input |
| `deployment.resource_lock` | none | Compute carries no lock |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "container_group" {
  source  = "Azure/avm-res-containerinstance-containergroup/azurerm"
  version = "~> 0.2.0"

  name                = data.naming_name.container_group.name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"

  # decision: container-instances.container_group.restart_policy - Bicep's default is Always
  restart_policy = "OnFailure"
  # decision: container-instances.container_group.availability_zone
  zones = []

  containers = {
    main = {
      image   = var.container_image # a tag or digest, never latest
      cpu     = 1
      memory  = 2
      ports   = []
      volumes = {}
    }
  }
  exposed_ports = []

  # decision: container-instances.networking.ip_address_type - injected into a delegated subnet
  subnet_ids = [var.subnet_id]

  managed_identities = { system_assigned = false, user_assigned_resource_ids = [var.user_assigned_identity_id] }
  image_registry_credential = {
    registry = {
      server                    = var.registry_login_server
      user_assigned_identity_id = var.user_assigned_identity_id
    }
  }
  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  # decision: container-instances.security.key_management - only for customer_managed
  key_vault_key_id                    = var.key_vault_key_id
  key_vault_user_assigned_identity_id = var.user_assigned_identity_id

  # logs only through the workspace id and key; the key is in state
  diagnostics_log_analytics = {
    workspace_id  = data.azurerm_log_analytics_workspace.this.workspace_id
    workspace_key = data.azurerm_log_analytics_workspace.this.primary_shared_key
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.container_group.resource_id }
output "ip_address" { value = module.container_group.ip_address }
```

For `public`, `subnet_ids` is `[]` and `exposed_ports` / `ports` list the ports. Omit
`key_vault_key_id` and its identity for `platform_managed`, `image_registry_credential` for a
public image, and `diagnostics_log_analytics` is rendered whenever a workspace is named. Input
member names and the output names are read from the README of the pinned version.

### Tests

With `azurerm` mocked, the module's outputs are `name`, `fqdn`, `ip_address`,
`resource_group_name` and `resource_id`: no `resource` output, so a plan observes nothing of the
group's configuration. Every decision is `# not-testable: <key> - set through the
module's <input>; the module's own tests cover the mapping`, and the call is the review - say so
in the handover. The root can assert what it computes itself: the empty or non-empty `subnet_ids`
that decides the address type, and the zone list.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; checked against `terraform providers schema -json`
(azurerm 5.11.0).

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
