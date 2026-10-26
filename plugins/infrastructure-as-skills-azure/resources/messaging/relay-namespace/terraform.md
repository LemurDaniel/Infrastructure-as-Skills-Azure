# Rendering an Azure Relay namespace as Terraform

Mapping from the question set to the namespace. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-relay-namespace/azurerm` | **v0.1.1** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.1`, on the
root module and on each submodule call.

**AzAPI-based with an `azurerm` constraint**: it takes `resource_group_id` (the group's id, not
its name) and requires `azapi ~> 2.4` **and** `azurerm ~> 4.0` - **a root calling it cannot be
on 5.x** - plus `modtm ~> 0.3`, `random ~> 3.5`, and Terraform `>= 1.9`. The root's provider set
is the union with the other modules. The root module validates the name (6-50 characters,
starts with a letter) at plan time.

**The children are submodules, not inputs.** The root module creates the namespace, its private
endpoints, role assignments, lock and diagnostic setting, and nothing else; hybrid connections,
WCF relays, authorization rules and the network rule set are `//modules/<name>` calls beside it
that take `relay_namespace_id`. The `authorization-rule` submodule is never called under
`local_auth: disabled`.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| tier (no decision) | `sku = { name = "Standard", tier = "Standard" }` | The module default; written because it is the only value and the module takes the object |
| `hybrid_connections` | `module "hybrid_connection"` (`//modules/hybrid-connection`), one per entry: `name`, `relay_namespace_id`, `user_metadata` | `user_metadata` is a JSON string; the App Service Hybrid Connection Manager reads `[{ key = "endpoint", value = "host:port" }]` |
| `client_authorization_required` | `requires_client_authorization` on each hybrid-connection call | Submodule default `true`; written |
| `wcf_relays` | `module "wcf_relay"` (`//modules/wcf-relay`), one per entry | Read the submodule README for `relay_type`; SAS-only, a named departure |
| `local_auth` | no input - the type has no switch; **no `authorization-rule` submodule call**, no `listKeys` | Recorded `forced`; roles only |
| `public_network_access` | `public_network_access` on the root | **A string** (`"Enabled"` / `"Disabled"`), module default `"Enabled"`; written |
| `ip_rules` | `module "network_rule_set"` (`//modules/network-rule-set`): `public_network_access = "Enabled"`, `default_action = "Deny"`, `ip_rules = [{ ipMask, action = "Allow" }]` | Called only under `enabled_with_firewall`; the key is `ipMask` (camel case), as the submodule spells it |
| `private_endpoint_subnet` | `private_endpoints = { namespace = { subnet_resource_id } }` | The sub-resource is `namespace`, fixed by the module |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy`; a zone group needs at least one zone id |
| `role_assignments` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | On the namespace; a per-connection role is an `azurerm_role_assignment` scoped to the submodule's `resource_id` |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`; emptied so the categories are the decision |
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | In the stages the deployment names |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "relay_namespace" {
  source  = "Azure/avm-res-relay-namespace/azurerm"
  version = "~> 0.1.1"

  name              = data.naming_name.relay_namespace.name
  location          = var.location
  resource_group_id = data.azurerm_resource_group.this.id

  # the one tier - no decision, written because the module takes the object
  sku = { name = "Standard", tier = "Standard" }

  # decision: relay-namespace.networking.public_network_access - a string, module default Enabled
  public_network_access = "Disabled"
  private_endpoints = {
    namespace = {
      name               = data.naming_name.relay_namespace_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: relay-namespace.access.local_auth - no authorization-rule submodule, no key output
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
      log_categories        = ["HybridConnectionsEvent", "VNetAndIPFilteringLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

# decision: relay-namespace.connections.hybrid_connections, client_authorization_required
module "hybrid_connection" {
  source  = "Azure/avm-res-relay-namespace/azurerm//modules/hybrid-connection"
  version = "~> 0.1.1"
  for_each = var.hybrid_connections

  name                          = each.value.name
  relay_namespace_id            = module.relay_namespace.resource_id
  requires_client_authorization = true
  user_metadata                 = each.value.endpoint == null ? null : jsonencode([{ key = "endpoint", value = each.value.endpoint }])
}

# decision: relay-namespace.networking.ip_rules - only under enabled_with_firewall
module "network_rule_set" {
  source  = "Azure/avm-res-relay-namespace/azurerm//modules/network-rule-set"
  version = "~> 0.1.1"
  count   = length(var.ip_rules) > 0 ? 1 : 0

  relay_namespace_id    = module.relay_namespace.resource_id
  public_network_access = "Enabled"
  default_action        = "Deny"
  ip_rules              = [for r in var.ip_rules : { ipMask = r, action = "Allow" }]
}

output "id" { value = module.relay_namespace.resource_id }
```

Under `enabled_with_firewall` the root's `public_network_access` is `"Enabled"` and the rule
set carries the allowlist; under `disabled` the rule-set call is omitted (the service ignores
rules then) and the root alone closes the namespace. A listener's and a sender's roles
(`Azure Relay Listener`, `Azure Relay Sender`) are granted on `module.hybrid_connection[k].resource_id`
by the pattern that owns both sides. A WCF relay entry adds a `//modules/wcf-relay` call and a
`Listen` rule through `//modules/authorization-rule` scoped to that relay - the one SAS case,
recorded as a departure.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the namespace
and every child are `azapi_resource`s, so asserts target `body.sku.name` and
`body.properties.publicNetworkAccess` on the namespace, `body.properties.requiresClientAuthorization`
and `userMetadata` on each hybrid connection, and `body.properties.defaultAction` /
`ipRules` on the rule set - exact paths are read off a first `terraform test` on the pinned
version. `local_auth` is asserted negatively: no `authorization-rule` module in the plan. The
endpoint, role assignments and the diagnostic setting are marked `# not-testable:` with a
reason where the plan does not show them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| tier | `azurerm_relay_namespace.sku_name = "Standard"` |
| `hybrid_connections`, `client_authorization_required` | `azurerm_relay_hybrid_connection { requires_client_authorization, user_metadata }` |
| `wcf_relays` | no `azurerm` resource - `azapi_resource` `Microsoft.Relay/namespaces/wcfRelays@2024-01-01` |
| `local_auth` | no `azurerm_relay_namespace_authorization_rule`, no `*_connection_string` output |
| `public_network_access`, `ip_rules` | no `azurerm` argument - `azapi_resource` `Microsoft.Relay/namespaces/networkRuleSets@2024-01-01` named `default` with `properties: { publicNetworkAccess, defaultAction, ipRules }`, or `azapi_update_resource` on the namespace for `properties.publicNetworkAccess` |
| `private_endpoint_subnet` | `azurerm_private_endpoint` with `subresource_names = ["namespace"]` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }`, `enabled_metric { category }` |
