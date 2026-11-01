# Rendering an Event Hubs namespace as Terraform

Mapping from the question set to the namespace. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-eventhub-namespace/azurerm` | **v0.1.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.1` - below 1.0 a
minor breaks, so it is the minor that is fixed, as for every pre-1.0 module.

**AzAPI-based with an `azurerm` constraint**: it takes `resource_group_name` (a name) and
requires `azapi ~> 2.12` **and** `azurerm ~> 4.0` - **a root calling it cannot be on 5.x** - plus
`modtm ~> 0.3`, `random ~> 3.6`, and Terraform `>= 1.9`. The root's provider set is the union
with the other modules. Parts of the module are driven by `resource_types` (the AzAPI type and
API version); leave them at their defaults.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "event_hubs" {
  source  = "Azure/avm-res-eventhub-namespace/azurerm"
  version = "~> 0.1.1"

  name                = data.naming_name.event_hubs.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: event-hubs.namespace.sku
  sku                  = "Standard"
  capacity             = 1
  auto_inflate_enabled = false
  # decision: event-hubs.namespace.local_auth - inverse input
  local_authentication_enabled = false

  # decision: event-hubs.networking.public_network_access - a bool
  public_network_access_enabled = false
  network_rulesets = {
    default_action                 = "Deny"
    public_network_access_enabled  = false
    trusted_service_access_enabled = false
    ip_rule                        = []
  }
  private_endpoints = {
    namespace = {
      name               = data.naming_name.event_hubs_private_endpoint.name
      subresource_name   = "namespace"
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  event_hubs = {
    for h in var.event_hubs : h => {
      # decision: event-hubs.entities.partition_count, message_retention_days
      namespace_name      = data.naming_name.event_hubs.name
      resource_group_name = var.resource_group_name
      partition_count     = 4
      message_retention   = 1
    }
  }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
      principal_type             = v.principal_type
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["OperationalLogs", "EventHubVNetConnectionEvent"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.event_hubs.resource_id }
```

### Consumer groups

```hcl
resource "azapi_resource" "consumer_group" {
  for_each = { for g in var.consumer_groups : "${g.event_hub}/${g.name}" => g }

  type      = "Microsoft.EventHub/namespaces/eventhubs/consumergroups@2024-01-01"
  name      = each.value.name
  parent_id = module.event_hubs.resource_id_eventhubs[each.value.event_hub] # read the output name from the README
}
```

`2024-01-01` is a GA version of the type (listed by `az provider show -n Microsoft.EventHub` on
2026-10-25; `2026-01-01` is newer). Look the current one up the same way. The event hub's id is
the module output the README names for it.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the
namespace is an `azapi_resource`, so asserts target its `body.sku`, `body.properties.disableLocalAuth`
and `publicNetworkAccess`, and each event hub's `body.properties.partitionCount` and
`messageRetentionInDays` - exact paths are read off a first `terraform test` on the pinned
version. The endpoint, role assignments and diagnostic setting are built by the module and
marked `# not-testable:` with a reason, as are `minimum_tls_version`, `zone_redundant` and
`infrastructure_encryption`, which the module has no input for.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
