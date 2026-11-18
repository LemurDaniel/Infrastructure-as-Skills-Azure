# Rendering an Event Grid custom topic as Terraform

Mapping from the question set to the topic. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-eventgrid-topic/azurerm` | **v0.1.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.1`.

**AzAPI-based with an `azurerm` constraint**: it takes `parent_id` (the resource group's id, not
its name) and requires `azapi ~> 2.4` **and** `azurerm ~> 4.0` - **a root calling it cannot be on 5.x** - plus
`modtm ~> 0.3`, `random ~> 3.5`, and Terraform `>= 1.9`. The root's provider set is the union
with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy`; a zone group needs at least one zone id |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "event_grid_topic" {
  source  = "Azure/avm-res-eventgrid-topic/azurerm"
  version = "~> 0.1.1"

  name      = data.naming_name.event_grid_topic.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: event-grid-topic.topic.input_schema - module default EventGridSchema
  input_schema                = "CloudEventSchemaV1_0"
  minimum_tls_version_allowed = "1.2"
  # decision: event-grid-topic.topic.local_auth
  disable_local_auth      = true
  data_residency_boundary = "WithinGeopair"

  # decision: event-grid-topic.networking.public_network_access - a string
  public_network_access = "Disabled"
  inbound_ip_rules      = []
  private_endpoints = {
    topic = {
      name               = data.naming_name.event_grid_topic_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  event_subscriptions = {
    for k, s in var.event_subscriptions : k => {
      name = s.name
      delivery_with_resource_identity = {
        identity    = { type = "UserAssigned", user_assigned_identity = var.delivery_identity_id }
        destination = s.destination
      }
      filter = s.filter
      # decision: event-grid-topic.delivery.max_delivery_attempts, event_ttl_minutes
      retry_policy = {
        max_delivery_attempts         = 30
        event_time_to_live_in_minutes = 1440
      }
      # decision: event-grid-topic.delivery.keep_undeliverable_events
      dead_letter_with_resource_identity = {
        identity = { type = "UserAssigned", user_assigned_identity = var.delivery_identity_id }
        dead_letter_destination = {
          storage_blob = {
            resource_id         = var.dead_letter_storage_account_id
            blob_container_name = "eventgrid-deadletter"
          }
        }
      }
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
      log_categories        = ["DeliveryFailures", "PublishFailures"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.event_grid_topic.resource_id }
```

A delivery destination and its role are wiring: the identity needs `Azure Service Bus Data
Sender`, `Azure Event Hubs Data Sender` or `Storage Queue Data Message Sender` on the target
before the subscription is created, and the pattern orders it. A webhook destination is an
`open:` entry, because the endpoint must answer the validation handshake when the subscription
is created.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the topic is
an `azapi_resource`, so asserts target its `body.properties` (`inputSchema`,
`disableLocalAuth`, `publicNetworkAccess`, `minimumTlsVersionAllowed`,
`dataResidencyBoundary`) - exact paths are read off a first `terraform test` on the pinned
version. The endpoint, role assignments, diagnostic setting and the subscriptions' nested
bodies are built by the module and marked `# not-testable:` with a reason where the plan does
not show them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
