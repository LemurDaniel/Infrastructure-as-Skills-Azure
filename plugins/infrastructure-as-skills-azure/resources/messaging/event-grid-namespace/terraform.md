# Rendering an Event Grid namespace as Terraform

Mapping from the question set to the namespace. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-eventgrid-namespace/azurerm` | **v0.1.2** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.2`.

**AzAPI-based with an `azurerm` constraint**: it takes `parent_id` (the resource group's id,
not its name) and requires `azapi ~> 2.4` **and** `azurerm ~> 4.0` - **a root calling it
cannot be on 5.x** - plus `modtm ~> 0.3`, `random ~> 3.5`, and Terraform `>= 1.9`. The root's
provider set is the union with the other modules.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `capacity` | `capacity`, with `sku = "Standard"` | Module defaults `1` and `"Standard"`; written. 1-20 |
| `minimum_tls_version` | **not carried by the module**; `azapi_update_resource` below | The API accepts `1.2` only |
| `local_auth` | no input - the type has no switch | Recorded `forced`; no `listKeys`, no key output. Roles only |
| `zone_redundant` | **not carried by the module** | The platform's regional default (`true` in a zonal region); fixed at creation, so an update resource cannot set it - a `false` in a zonal region is authored |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `namespace_topics`, `event_retention_days` | `namespace_topics = { <k> = { name, event_retention_days, input_schema = "CloudEventSchemaV1_0" } }` | Module default 7 days; written |
| `topic_subscriptions`, `delivery_mode` | `topic_event_subscriptions = { <k> = { topic_key, name, delivery_mode = "Queue" / "Push", destination, delivery_identity, filters_configuration } }` | A push subscription takes `destination` + `delivery_identity = { type = "SystemAssigned" }`; a queue one neither |
| `event_retention_days` (again) | `topic_event_subscriptions.<k>.event_time_to_live` | ISO 8601, `"P7D"`; module default `"P1D"` |
| `max_delivery_count` | `topic_event_subscriptions.<k>.max_delivery_count` | Module default 30, service default 10; written |
| `receive_lock_duration_seconds` | `topic_event_subscriptions.<k>.receive_lock_duration_in_seconds` | |
| `keep_undeliverable_events`, `dead_letter_*` | `topic_event_subscriptions.<k>.dead_letter_destination = { storage_account_id, blob_container_name, identity_type = "SystemAssigned" }` | The identity form; no key |
| `mqtt_broker` | **not carried by the module** - `topic_spaces_configuration` has no `state`; `azapi_update_resource` below | Cannot be disabled again once `Enabled` |
| `topic_spaces` | `topic_spaces = { <k> = { name, topic_templates } }` | |
| `clients` | `clients = { <k> = { name, authentication_name, attributes, client_certificate_authentication } }` | |
| `client_groups` | `client_groups = { <k> = { name, query } }` | |
| `permission_bindings` | `permission_bindings = { <k> = { name, client_group_key, topic_space_key, permission } }` | Map **keys** of the group and the space, not names |
| `mqtt_routing`, `mqtt_routing_topic` | `topic_spaces_configuration = { route_topic_resource_id }` | Two-pass when the topic is created in the same run |
| `public_network_access` | `public_network_access` | **A string** (`"Enabled"` / `"Disabled"`), module default `"Enabled"`; written |
| `ip_rules` | `inbound_ip_rules = [{ ip_mask, action = "Allow" }]` | Used only with public access `Enabled` |
| `private_endpoint_subnet` | `private_endpoints = { topic = { subnet_resource_id } }` | The sub-resource is `topic`, fixed by the module |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy`; a zone group needs at least one zone id |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`; emptied so the categories are the decision |
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | In the stages the deployment names |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |
| `deployment.key_management` | `customer_managed_key` exists as an input but the type has no key property | Not written; recorded as not applicable |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "event_grid_namespace" {
  source  = "Azure/avm-res-eventgrid-namespace/azurerm"
  version = "~> 0.1.2"

  name      = data.naming_name.event_grid_namespace.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: event-grid-namespace.namespace.capacity - the one tier, sized in units
  sku      = "Standard"
  capacity = 1

  # decision: event-grid-namespace.namespace.managed_identity
  managed_identities = { system_assigned = true }

  # decision: event-grid-namespace.networking.public_network_access - a string, module default Enabled
  public_network_access = "Disabled"
  inbound_ip_rules      = []
  private_endpoints = {
    topic = {
      name               = data.naming_name.event_grid_namespace_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: event-grid-namespace.topics.namespace_topics, event_retention_days
  namespace_topics = {
    for k, t in var.namespace_topics : k => {
      name                 = t.name
      event_retention_days = 7
      input_schema         = "CloudEventSchemaV1_0"
    }
  }

  topic_event_subscriptions = {
    for k, s in var.topic_subscriptions : k => {
      topic_key = s.topic_key
      name      = s.name
      # decision: event-grid-namespace.topics.delivery_mode
      delivery_mode         = s.delivery_mode
      event_delivery_schema = "CloudEventSchemaV1_0"
      # decision: event-grid-namespace.topics.event_retention_days - the subscription's TTL follows the topic
      event_time_to_live = "P7D"
      # decision: event-grid-namespace.topics.max_delivery_count - module default 30
      max_delivery_count = 10
      # decision: event-grid-namespace.topics.receive_lock_duration_seconds
      receive_lock_duration_in_seconds = 60
      # decision: event-grid-namespace.topics.keep_undeliverable_events
      dead_letter_destination = {
        storage_account_id  = var.dead_letter_storage_account_id
        blob_container_name = "eventgrid-deadletter"
        identity_type       = "SystemAssigned"
      }
      filters_configuration = { included_event_types = s.included_event_types }
    }
  }

  # decision: event-grid-namespace.mqtt.* - content, empty while mqtt_broker is false
  topic_spaces        = var.topic_spaces
  clients             = var.clients
  client_groups       = var.client_groups
  permission_bindings = var.permission_bindings

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
      log_categories        = ["FailedHttpDataPlaneOperations", "FailedMqttConnections", "FailedMqttPublishedMessages", "MqttDisconnections"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

# decision: event-grid-namespace.namespace.minimum_tls_version, mqtt.mqtt_broker - not carried by the module
resource "azapi_update_resource" "event_grid_namespace_settings" {
  type        = "Microsoft.EventGrid/namespaces@2025-02-15"
  resource_id = module.event_grid_namespace.resource_id
  body = {
    properties = {
      minimumTlsVersionAllowed = "1.2"
      topicSpacesConfiguration = {
        state = "Disabled"
      }
    }
  }
}

output "id" { value = module.event_grid_namespace.resource_id }
```

With `mqtt_broker: true` the update resource writes `state = "Enabled"`, the module call adds
`topic_spaces_configuration = { route_topic_resource_id = var.mqtt_routing_topic_id }` when
`mqtt_routing` says so, and the MQTT maps are filled from the spec. The update resource
depends on the module implicitly through `resource_id`; the module's own `azapi_resource`
does not write the two properties, so the two do not fight over them.

A push subscription replaces the queue block with `destination = { endpointType = "ServiceBusQueue",
properties = { resourceId = ... } }` and `delivery_identity = { type = "SystemAssigned" }`; the
identity needs `Azure Service Bus Data Sender`, `Azure Event Hubs Data Sender` or `Storage
Queue Data Message Sender` on the target before the subscription is created, and the pattern
orders it. A webhook destination is an `open:` entry, because the endpoint must answer the
validation handshake.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the
namespace is an `azapi_resource`, so asserts target its `body.sku.capacity`,
`body.properties.publicNetworkAccess` and `body.properties.inboundIpRules`, and the update
resource's `body.properties.minimumTlsVersionAllowed` and `topicSpacesConfiguration.state` -
exact paths are read off a first `terraform test` on the pinned version. The namespace topics,
subscriptions and MQTT children are submodules with their own `azapi_resource` bodies
(`properties.eventRetentionInDays`, `properties.deliveryConfiguration.*`) and are asserted
there. `zone_redundant` is `# not-testable:` (no input, the platform decides); the endpoint,
role assignments and the diagnostic setting are marked `# not-testable:` with a reason where
the plan does not show them.

## Authored rendering

The fallback, and the path for a `zone_redundant: false` in a zonal region. `azurerm` has no
resource for the namespace; the authored render is `azapi_resource` with
`type = "Microsoft.EventGrid/namespaces@2025-02-15"`:

| Decision | Body |
|---|---|
| `capacity` | `sku = { name = "Standard", capacity }` |
| `minimum_tls_version` | `properties.minimumTlsVersionAllowed` |
| `zone_redundant` | `properties.isZoneRedundant` |
| `public_network_access`, `ip_rules` | `properties.publicNetworkAccess`, `properties.inboundIpRules[{ ipMask, action }]` |
| `managed_identity` | `identity { type, identity_ids }` |
| `mqtt_broker`, `mqtt_routing*` | `properties.topicSpacesConfiguration = { state, routeTopicResourceId, routingIdentityInfo }` |
| `namespace_topics`, `topic_subscriptions` | child `Microsoft.EventGrid/namespaces/topics@2025-02-15` and `.../topics/eventSubscriptions@2025-02-15` |
| MQTT content | child `topicSpaces`, `clients`, `clientGroups`, `permissionBindings`, `caCertificates` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
