# Rendering an Event Grid system topic as Terraform

Mapping from the question set to the topic. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-eventgrid-systemtopic/azurerm` | none published | 2026-10-26 | **Proposed** in the index; the registry has no versions |

A `Proposed` module is not used ([avm.md](../../../core/iac-rendering/references/avm.md), *Status
decides whether it is used*). **The authored rendering below is the primary path** for this
resource until the module reaches `Available`; re-check the index before a render, and when a
version exists, walk the decisions against its inputs before switching.

## Authored rendering

Targets `azurerm` **5.x**; check arguments against `terraform providers schema -json`. The
subscription resource renamed its endpoint arguments in 5.x: `service_bus_queue_id`,
`service_bus_topic_id`, `eventhub_id`, `hybrid_connection_id` (4.x had `*_endpoint_id`), and
the diagnostic setting takes `enabled_metric` (4.x: `metric`).

### Decision -> argument

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Arguments no decision covers

| Input | Argument | Note |
|---|---|---|
| `managed_identity`, `user_assigned_identity_ids` | `.identity { type, identity_ids }` | `SystemAssigned`, `UserAssigned` or both |
| subject filter (content of the entry) | `subject_filter { subject_begins_with, subject_ends_with }` | |
| `deployment.resource_lock` | no lock - the type is not on the list | |
| `context.tags` | `tags = local.tags` on the topic | A subscription has no tags |

### The call

```hcl
resource "azurerm_eventgrid_system_topic" "this" {
  name                = data.naming_name.event_grid_system_topic.name
  resource_group_name = var.resource_group_name
  # decision: event-grid-system-topic.placement.location - the source's region, global for Microsoft.Resources.*
  location = var.location
  # decision: event-grid-system-topic.source.source_resource, topic_type - both fixed at creation
  source_resource_id = var.source_resource_id
  topic_type         = "Microsoft.Storage.StorageAccounts"

  # decision: event-grid-system-topic.source.managed_identity
  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_eventgrid_system_topic_event_subscription" "this" {
  for_each = var.event_subscriptions

  name                = each.value.name
  system_topic        = azurerm_eventgrid_system_topic.this.name
  resource_group_name = var.resource_group_name

  # decision: event-grid-system-topic.delivery.destination_kind - one endpoint argument per kind
  service_bus_queue_id = each.value.target_id
  # decision: event-grid-system-topic.source.managed_identity - delivery with the topic's identity, no key
  delivery_identity {
    type = "SystemAssigned"
  }

  # decision: event-grid-system-topic.delivery.event_delivery_schema
  event_delivery_schema = "CloudEventSchemaV1_0"
  # decision: event-grid-system-topic.delivery.included_event_types - empty delivers every type
  included_event_types = each.value.included_event_types
  subject_filter {
    subject_begins_with = each.value.subject_begins_with
  }

  # decision: event-grid-system-topic.delivery.max_delivery_attempts, event_ttl_minutes
  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440
  }

  # decision: event-grid-system-topic.delivery.keep_undeliverable_events, dead_letter_*
  storage_blob_dead_letter_destination {
    storage_account_id          = var.dead_letter_storage_account_id
    storage_blob_container_name = "eventgrid-deadletter"
  }
  dead_letter_identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "this" {
  for_each = var.role_assignments

  scope                = azurerm_eventgrid_system_topic.this.id
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
  principal_type       = each.value.principal_type
}

# decision: event-grid-system-topic.observability.diagnostic_workspace, diagnostic_categories, metrics_enabled
resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "diag-${azurerm_eventgrid_system_topic.this.name}"
  target_resource_id         = azurerm_eventgrid_system_topic.this.id
  log_analytics_workspace_id = var.diagnostic_workspace_id

  enabled_log {
    category = "DeliveryFailures"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}

output "id" { value = azurerm_eventgrid_system_topic.this.id }
output "principal_id" { value = azurerm_eventgrid_system_topic.this.identity[0].principal_id }
```

A mixed set of destination kinds renders the endpoint argument per entry (`each.value.kind`
switches between `service_bus_queue_id`, `eventhub_id`, a `storage_queue_endpoint` block and so
on - one `dynamic` block or one resource per kind, whichever reads better). The identity needs
`Azure Service Bus Data Sender`, `Azure Event Hubs Data Sender` or `Storage Queue Data Message
Sender` on the target and `Storage Blob Data Contributor` on the dead-letter container before
the subscription is created; the pattern grants and orders it, with a `time_sleep` after the
role assignment. A webhook destination is an `open:` entry, because the endpoint must answer the
validation handshake; `user_assigned` replaces `type` with `"UserAssigned"` and adds
`user_assigned_identity` on both identity blocks.

### Tests

`mock_provider "azurerm"` keeps the plan credential-free. Everything is a plain `azurerm`
resource, so every decision is observable: `azurerm_eventgrid_system_topic.this.topic_type`,
`.source_resource_id`, `.location`, `.identity[0].type`; on the subscription
`event_delivery_schema`, `included_event_types`, `retry_policy[0].max_delivery_attempts`,
`retry_policy[0].event_time_to_live`, `storage_blob_dead_letter_destination[0].storage_blob_container_name`,
`delivery_identity[0].type`, `service_bus_queue_id`; on the diagnostic setting
`enabled_log[*].category` and `enabled_metric[*].category`. Nothing is `# not-testable:` by
construction; the role assignments are, when the principal is unknown at plan time.

## With the AVM module, once it exists

When `avm-res-eventgrid-systemtopic` reaches `Available`, the expected shape by analogy with
the topic module is `source_resource_id`, `topic_type`, `managed_identities`,
`event_subscriptions = { <k> = { name, delivery_with_resource_identity, retry_policy,
dead_letter_with_resource_identity, filter } }`, `role_assignments`, `diagnostic_settings`,
`enable_telemetry`, `tags`. Read the pinned README; do not render from this paragraph.
