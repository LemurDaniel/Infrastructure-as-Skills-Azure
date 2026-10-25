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

| Decision | Input | Note |
|---|---|---|
| `sku` | `sku` | Module default `Standard`; written |
| `capacity` | `capacity` | Default 1; written |
| `auto_inflate`, `maximum_throughput_units` | `auto_inflate_enabled`, `maximum_throughput_units` | Standard only; default off |
| `minimum_tls_version` | - | **No input** in this version; the platform default applies. Named in the handover, `# not-testable:` |
| `local_auth` | `local_authentication_enabled` | **Inverse**: `disabled` is `false`; module default `false`, written |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default `false`. Also a member of `network_rulesets` |
| `public_network_access`, `ip_rules`, `trusted_service_bypass` | `network_rulesets = { default_action, public_network_access_enabled, trusted_service_access_enabled, ip_rule = [{ ip_mask }] }` | `public_network_access_enabled` and `trusted_service_access_enabled` are **required members**; `default_action` defaults to `Deny`. The README says "Requires Premium SKU": check it against the tier before relying on a firewall below Premium |
| `private_endpoint_subnet` | `private_endpoints = { namespace = { subnet_resource_id, subresource_name = "namespace" } }` | Standard or above |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | Version unset: the latest |
| `infrastructure_encryption` | - | **No input.** Taken from the platform; named in the handover |
| `event_hubs`, `partition_count`, `message_retention_days` | `event_hubs = { <name> = { namespace_name, resource_group_name, partition_count, message_retention } }` | `namespace_name` and `resource_group_name` are **required members of every entry**; `message_retention` is days |
| `event_archive`, `archive_*` | `event_hubs.<k>.capture_description = { enabled, encoding, interval_in_seconds, destination = { archive_name_format, blob_container_name, storage_account_id } }` | `encoding` `Avro`; destination `name` stays `EventHubArchive.AzureBlockBlob` |
| `consumer_groups` | - | **No input.** One `azapi_resource` of type `Microsoft.EventHub/namespaces/eventhubs/consumergroups` per name, outside the module |
| `zone_redundant` | - | **No input**; `# not-testable:` |
| `geo_recovery`, `partner_namespace` | - | **No input.** A `azapi_resource` of type `Microsoft.EventHub/namespaces/disasterRecoveryConfigs` on the primary, outside the module |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | Also per event hub |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | Read the member names for the pinned version |
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

| Decision | Argument |
|---|---|
| `sku`, `capacity` | `azurerm_eventhub_namespace.sku`, `.capacity` |
| `auto_inflate`, `maximum_throughput_units` | `.auto_inflate_enabled`, `.maximum_throughput_units` |
| `minimum_tls_version` | `.minimum_tls_version` |
| `local_auth` | `.local_authentication_enabled` |
| `public_network_access` | `.public_network_access_enabled` |
| `network_rulesets` | `.network_rulesets { default_action, public_network_access_enabled, trusted_service_access_enabled, ip_rule, virtual_network_rule }` |
| `managed_identity` | `.identity { type, identity_ids }` |
| `key_management` | `azurerm_eventhub_namespace_customer_managed_key` |
| `event_hubs` | `azurerm_eventhub` with `partition_count`, `message_retention`, `capture_description` |
| `consumer_groups` | `azurerm_eventhub_consumer_group` |
| `geo_recovery` | `azurerm_eventhub_namespace_disaster_recovery_config` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
