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

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku` | Module default **`Premium`**; written |
| `capacity` | `capacity` | Premium only, `1/2/4/8/16`. Standard and Basic take `0` |
| `zone_redundant` | - | **No input.** Zone redundancy is the platform's on Premium in a zonal region; the decision is not testable in a plan and is `# not-testable:` |
| `premium_messaging_partitions` | `premium_messaging_partitions` | Premium only; `0` for Standard/Basic |
| `minimum_tls_version` | `minimum_tls_version` | Default `"1.2"`; written |
| `local_auth` | `local_auth_enabled` | **Inverse**: `disabled` is `false`; module default **`true`** |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default **`true`** |
| `public_network_access`, `ip_rules`, `trusted_service_bypass` | `network_rule_config = { default_action, cidr_or_ip_rules, trusted_services_allowed }` | Module default `default_action = "Allow"`: set `"Deny"` for every posture except `enabled`. Premium only in Azure, whatever the README says for Basic/Standard |
| `private_endpoint_subnet` | `private_endpoints = { namespace = { subnet_resource_id, subresource_name = "namespace" } }` | `subresource_name` is optional and defaults to `null`: written. Premium only |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | Premium; read the exact member names from the README |
| `infrastructure_encryption` | `infrastructure_encryption_enabled` | Module default **`true`** and then requires the key; written |
| `queues` | `queues = { <name> = { ... } }` | One entry per name; the namespace-wide settings below on each |
| `topics` | `topics = { <name> = { subscriptions = { <name> = { ... } } } }` | Standard or Premium; Basic ignores it |
| `message_ordering` | `queues.<k>.requires_session`, `topics.<k>.subscriptions.<s>.requires_session` | Fixed at creation |
| `duplicate_protection` | `queues.<k>.requires_duplicate_detection`, `topics.<k>.requires_duplicate_detection` | Fixed at creation; not on Basic |
| `message_retention_days` | `default_message_ttl` | ISO 8601: `P14D` |
| `dead_letter_on_expiry` | `dead_lettering_on_message_expiration` | Queue and subscription; module default `false` |
| `max_delivery_count` | `max_delivery_count` | Queue and subscription; default `10` |
| `lock_duration_seconds` | `lock_duration` | Queue and subscription; `PT1M` for 60 |
| `max_size_megabytes` | `max_size_in_megabytes` | Queue and topic |
| `geo_recovery`, `partner_namespace` | - | **No input.** A `azurerm_servicebus_namespace_disaster_recovery_config` outside the module, see below |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | Also per queue and topic |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories. **The module validates `log_categories`** against `OperationalLogs`, `VNetAndIPFilteringLogs`, `RuntimeAuditLogs`, `ApplicationMetricsLogs`: `DiagnosticErrorLogs` is refused |
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

| Decision | Argument on `azurerm_servicebus_namespace` |
|---|---|
| `sku`, `capacity`, `premium_messaging_partitions` | `sku`, `capacity`, `premium_messaging_partitions` |
| `minimum_tls_version` | `minimum_tls_version` |
| `local_auth` | `local_auth_enabled` |
| `public_network_access` | `public_network_access_enabled` (a bool, unchanged in 5.x; only storage moved to a string) |
| `network_rule_config` | `.network_rule_set { default_action, public_network_access_enabled, trusted_services_allowed, ip_rules, network_rules }` (an inline block in 5.x) |
| `managed_identity` | `identity { type, identity_ids }` |
| `key_management` | `customer_managed_key { key_vault_key_id, identity_id, infrastructure_encryption_enabled }` |
| `queues` | `azurerm_servicebus_queue` per name, `namespace_id` |
| `topics` | `azurerm_servicebus_topic` and `azurerm_servicebus_subscription` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
