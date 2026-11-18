# Rendering a Traffic Manager profile as Terraform

Mapping from the question set to the profile. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-trafficmanagerprofile/azurerm` | **v0.1.1** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.1`; the module is
at its first minor, so expect inputs to move.

**AzAPI only**: it takes `resource_group_name` (a name, not an id), has no `location` input (the
profile is global inside the module) and requires `azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.5`,
Terraform `~> 1.5`; no `azurerm`. The root keeps `azurerm` for its data sources. The endpoints are
three child modules, one per kind.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.1.1: nothing from this question set. `allowed_endpoint_record_types`,
`lock`, `custom_headers`, `always_serve`, `subnets` and `geo_mapping` are inputs the question set
has no decision for (the last two are filled from an `endpoints` entry when the method needs them).

### The call

```hcl
data "naming_name" "traffic_manager" {
  resource = "Azure::Microsoft.Network/trafficManagerProfiles"
}

module "traffic_manager" {
  source  = "Azure/avm-res-network-trafficmanagerprofile/azurerm"
  version = "~> 0.1.1"

  name                = data.naming_name.traffic_manager.name
  resource_group_name = var.resource_group_name

  # decision: traffic-manager.profile.routing_method - forced by traffic_goal: failover
  traffic_routing_method = "Priority"
  # decision: traffic-manager.profile.relative_dns_name (empty: the resource name), dns_ttl_seconds
  dns_config = {
    relative_name = data.naming_name.traffic_manager.name
    ttl           = 60
  }
  # decision: traffic-manager.profile.profile_status
  profile_status = "Enabled"
  # decision: traffic-manager.profile.traffic_view
  traffic_view_enrollment_status = "Disabled"
  # decision: traffic-manager.profile.max_return - MultiValue only
  max_return = null

  # decision: traffic-manager.monitoring.monitor_protocol, monitor_port, monitor_path, expected_status_codes, probe_profile (standard)
  monitor_config = {
    protocol                     = "HTTPS"
    port                         = 443
    path                         = "/health"
    interval_in_seconds          = 30
    timeout_in_seconds           = 10
    tolerated_number_of_failures = 3
    expected_status_code_ranges  = [{ min = 200, max = 299 }]
  }

  # decision: traffic-manager.endpoints.endpoints
  azure_endpoints = {
    for k, e in var.endpoints : k => {
      name               = e.name
      target_resource_id = e.target_resource_id
      priority           = e.priority
      endpoint_location  = e.location
      enabled            = true
    }
  }
  external_endpoints = {}
  nested_endpoints   = {}

  # decision: traffic-manager.access.role_assignments
  role_assignments = {}

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      # decision: traffic-manager.observability.diagnostic_categories
      log_categories = ["ProbeHealthStatusEvents"]
      log_groups     = []
      # decision: traffic-manager.observability.metrics_enabled
      metric_categories = ["AllMetrics"]
    }
  }

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "fqdn" { value = module.traffic_manager.fqdn } # the public zone's CNAME target
output "id" { value = module.traffic_manager.resource_id }
```

Validated with `terraform validate` (registry, v0.1.1, `azapi ~> 2.12`, with `azurerm ~> 4.0` in
the root). `fqdn` is what `wiring.dns_records` carries into the `public-dns-zone` render.

### Tests

`mock_provider "azapi"`, `"modtm"` and `"random"`; the naming provider stays real. The module
exposes `name`, `fqdn`, `resource_id` and the three endpoint maps as outputs and **no `resource`
output**; the profile's body is an `azapi_resource` inside the module and the endpoints are child
modules, so a plan shows the name and nothing of the decisions. Each is marked `# not-testable:`
with that reason:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.traffic_manager.name == "traf-gwc-dev-shop-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

# not-testable: traffic-manager.profile.traffic_goal - pre-answers routing_method; nothing of its own
# not-testable: traffic-manager.profile.routing_method - the profile is an azapi_resource inside the module without a resource output
# not-testable: traffic-manager.profile.relative_dns_name - as above; fqdn is unknown at plan
# not-testable: traffic-manager.profile.dns_ttl_seconds - as above
# not-testable: traffic-manager.profile.profile_status - as above
# not-testable: traffic-manager.profile.traffic_view - as above
# not-testable: traffic-manager.profile.max_return - as above
# not-testable: traffic-manager.monitoring.monitor_protocol - as above
# not-testable: traffic-manager.monitoring.monitor_port - as above
# not-testable: traffic-manager.monitoring.monitor_path - as above
# not-testable: traffic-manager.monitoring.expected_status_codes - as above
# not-testable: traffic-manager.monitoring.probe_profile - as above
# not-testable: traffic-manager.endpoints.endpoints - child modules; their count is in the plan JSON
# not-testable: traffic-manager.access.role_assignments - inside the module
# not-testable: traffic-manager.observability.diagnostic_workspace - the diagnostic setting is inside the module
# not-testable: traffic-manager.observability.diagnostic_categories - as above
# not-testable: traffic-manager.observability.metrics_enabled - as above
```

`terraform show -json` on the saved plan shows `Microsoft.Network/trafficmanagerprofiles@2024-04-01-preview`
with `properties.trafficRoutingMethod`, `dnsConfig`, `monitorConfig` and the endpoint children; a
pipeline check over that file is the place for these.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Resource / argument |
|---|---|
| the profile | `azurerm_traffic_manager_profile` (`name`, `resource_group_name`; no `location`) |

Validated against `azurerm` 5.x.
