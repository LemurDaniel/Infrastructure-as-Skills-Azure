# Rendering a Service Bus namespace as Terraform

Mapping from the question set to the namespace. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-servicebus-namespace/azurerm` | **0.4.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.4.0`. The tags
carry no `v` prefix.

**`azurerm`-based**: it takes `resource_group_name` (a name) and requires `azurerm ~> 4.14` - **a
root calling it cannot be on 5.x** - plus `modtm ~> 0.3`, `random ~> 3.6`, and Terraform
`>= 1.9`. It does not need `azapi`. The root's provider set is the union with the other modules.

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
module "service_bus" {
  source  = "Azure/avm-res-servicebus-namespace/azurerm"
  version = "~> 0.4.0"

  name                = data.naming_name.service_bus.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: service-bus.namespace.sku - the module default is Premium
  sku                          = "Premium"
  capacity                     = 1
  premium_messaging_partitions = 1
  # decision: service-bus.namespace.minimum_tls_version
  minimum_tls_version = "1.2"
  # decision: service-bus.namespace.local_auth - inverse input, module default true
  local_auth_enabled = false
  # decision: service-bus.encryption.infrastructure_encryption - module default true
  infrastructure_encryption_enabled = false

  # decision: service-bus.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  network_rule_config = {
    default_action           = "Deny"
    trusted_services_allowed = false
    cidr_or_ip_rules         = []
  }
  private_endpoints = {
    namespace = {
      name               = data.naming_name.service_bus_private_endpoint.name
      subresource_name   = "namespace"
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  queues = {
    for q in var.queues : q => {
      # decision: service-bus.entities.* - written on every queue
      requires_session                     = false
      requires_duplicate_detection         = false
      default_message_ttl                  = "P14D"
      dead_lettering_on_message_expiration = true
      max_delivery_count                   = 10
      lock_duration                        = "PT1M"
      max_size_in_megabytes                = 1024
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
      # decision: service-bus.observability.diagnostic_categories - log_groups defaults to allLogs
      log_categories    = ["OperationalLogs", "VNetAndIPFilteringLogs"]
      log_groups        = []
      metric_categories = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.service_bus.resource_id }
```

### Geo recovery

The module has no input for it. With `geo_recovery: paired_namespace` the secondary namespace is a
second call of the same module (another `location`, same SKU and capacity, **no entities**) and the
pairing is one resource outside both:

```hcl
resource "azurerm_servicebus_namespace_disaster_recovery_config" "pairing" {
  name                 = data.naming_name.service_bus_pairing.name
  primary_namespace_id = module.service_bus.resource_id
  partner_namespace_id = var.partner_namespace_id
}
```

### Tests

`mock_provider "azurerm"` (and `modtm`) keep the plan credential-free. The module is
`azurerm`-based, so asserts target what the plan shows on the namespace
(`sku`, `local_auth_enabled`, `public_network_access_enabled`, `minimum_tls_version`) and on each
queue and subscription resource; the exact addresses are read off a first `terraform test` run on
the pinned version, not recalled. The private endpoint, role assignments and diagnostic setting
are built by the module and marked `# not-testable:` with a reason, as for storage;
`zone_redundant` has no input and is `# not-testable:` too.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the namespace
this way. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
