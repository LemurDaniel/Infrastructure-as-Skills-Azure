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

| Decision | Input | Note |
|---|---|---|
| `container_image`, `cpu`, `memory_in_gb` | `containers = { main = { image, cpu, memory, ports, volumes = {} } }` | `cpu` and `memory` are numbers (GB); `ports` and `volumes` are required members, empty here |
| (OS) | `os_type = "Linux"` | Required input |
| `restart_policy` | `restart_policy` | Required input; Bicep defaults to `Always` |
| `availability_zone` | `zones` | List of strings; `[]` for `none` |
| `ip_address_type` | `subnet_ids` | The module derives `Private` from a non-empty list and `Public` otherwise; there is no type input |
| `subnet_id` | `subnet_ids = [ <id> ]` | |
| `exposed_ports` | `exposed_ports = [{ port, protocol }]` and the container's `ports` | Both lists must agree |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `registry_login_server` | `image_registry_credential = { <k> = { server, user_assigned_identity_id } }` | Never `username` / `password`; only a user-assigned identity |
| `role_assignments` | `role_assignments` | |
| `key_management`, `cmk_key_vault_key_id` | `key_vault_key_id`, `key_vault_user_assigned_identity_id` | The key id as the provider takes it (versioned); the identity is the group's |
| `diagnostic_workspace` | `diagnostics_log_analytics = { workspace_id, workspace_key }` | `workspace_id` is the workspace's customer id (a GUID), not its resource id; the key is sensitive and in state |
| `log_type` | none | **Not carried by the module**; named in the handover |
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

| Decision | Argument on `azurerm_container_group` |
|---|---|
| `restart_policy`, `availability_zone` | `restart_policy`, `zones` |
| `ip_address_type`, `subnet_id` | `ip_address_type` (`Public`, `Private`), `subnet_ids` |
| `container_image`, `cpu`, `memory_in_gb`, `exposed_ports` | `container { name, image, cpu, memory, ports { port, protocol } }` and `exposed_port { port, protocol }` |
| `managed_identity` | `identity { type, identity_ids }` |
| `registry_login_server` | `image_registry_credential { server, user_assigned_identity_id }` |
| `key_management` | `key_vault_key_id`, `key_vault_user_assigned_identity_id` |
| `diagnostic_workspace`, `log_type` | `diagnostics { log_analytics { workspace_id, workspace_key, log_type } }` |
| `role_assignments` | `azurerm_role_assignment` |
