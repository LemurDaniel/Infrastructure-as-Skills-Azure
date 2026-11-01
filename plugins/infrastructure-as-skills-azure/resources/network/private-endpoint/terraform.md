# Rendering a standalone private endpoint as Terraform

Mapping from the question set to the private endpoint. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
A resource whose module carries `private_endpoints` renders its endpoints there - see
[notes.md](notes.md#when-this-set-is-used-and-when-it-is-not).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-network-privateendpoint/azurerm` | **v0.3.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**AzAPI only**: it takes `parent_id` (the resource group's id) and requires `azapi ~> 2.12`,
`time ~> 0.13` and Terraform **`>= 1.16`**; no `azurerm`. Version 0.2.0 was `azurerm`-based; a
repository on it migrates with `avm_managed_migration_enabled`, set for one apply only.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `target_resource` | `private_connection_resource_id` | |
| `subresource` | `subresource_names = ["<group id>"]` | A list, with one entry |
| `connection_approval: manual` | not carried | The module has no manual-connection input at v0.3.0: render the endpoint authored (below) or mark the decision as not carried in the handover |
| `approval_message` | not carried | As above |
| `subnet` | `subnet_resource_id` | From the platform or the network set |
| `private_ip_address` | `ip_configurations = { <k> = { name, private_ip_address, subresource_name } }` | Omit for Azure-assigned |
| `dns_zone_group: attached` | `private_dns_zone_group_name`, `private_dns_zone_resource_ids` | |
| `dns_zone_group: left_to_policy` | neither input | No zone group is rendered, so there is no second writer |
| `dns_zones` | `private_dns_zone_resource_ids` | Ids; for a platform zone from the `data` source, for one created here the `private-dns-zone` output |
| the name | `name`, `network_interface_name`, `private_service_connection_name` | The interface name is required by the module although its description says optional; both follow the endpoint's name |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.3.0: the **manual connection** (`connection_approval:
manual`, `approval_message`). The decision stays in the spec; the render uses the authored
fallback for that endpoint.

### The call

```hcl
data "naming_name" "private_endpoint" {
  resource   = "Azure::Microsoft.Network/privateEndpoints"
  parameters = { subname = "vault" } # the sub-resource, so the index stays last
}

module "private_endpoint" {
  source  = "Azure/avm-res-network-privateendpoint/azurerm"
  version = "~> 0.3.0"

  name      = data.naming_name.private_endpoint.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  # decision: private-endpoint.target.target_resource
  private_connection_resource_id = var.target_resource_id
  # decision: private-endpoint.target.subresource - one group id per endpoint
  subresource_names = ["vault"]
  # decision: private-endpoint.networking.subnet
  subnet_resource_id = var.private_endpoint_subnet_id

  # Required by the module although its description says optional.
  network_interface_name          = "${data.naming_name.private_endpoint.name}-nic"
  private_service_connection_name = "psc-${data.naming_name.private_endpoint.name}"

  # decision: private-endpoint.dns.dns_zone_group - attached. For left_to_policy leave both
  # inputs out: no zone group is rendered and the platform policy writes the record.
  private_dns_zone_group_name   = "default"
  private_dns_zone_resource_ids = var.private_dns_zone_ids

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.private_endpoint.resource_id }
output "private_ip_addresses" { value = module.private_endpoint.private_ip_addresses }
```

Validated with `terraform validate` (registry, v0.3.0) in a root together with the other four
modules of this family. With several sub-resources the call sits in a `for_each` over the
group ids, one endpoint each, the key being the group id so the address reads as the decision
does (`module.private_endpoint["blob"]`).

### Tests

`mock_provider "azapi"`; the naming provider stays real. The module exposes no `resource`
output - its outputs are `name`, `resource_id`, `network_interface_ids`, `private_ip_addresses`
and `application_security_group_association_ids`, all but the name unknown at plan - so the
decisions are in the plan only as the `azapi_resource` body, which `terraform test` cannot
read, and are marked `# not-testable:` with that reason. Settled by a `terraform test` run on v0.3.0:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.private_endpoint.name == "pep-gwc-dev-telemetry-vault-01"
    error_message = "The name must come from naming.yaml, with the sub-resource before the index."
  }
}

# not-testable: private-endpoint.target.target_resource - inside the module's azapi_resource body; no resource output
# not-testable: private-endpoint.target.subresource - as above
# not-testable: private-endpoint.target.connection_approval - not carried by the module; authored when manual
# not-testable: private-endpoint.target.approval_message - as above
# not-testable: private-endpoint.networking.subnet - inside the body
# not-testable: private-endpoint.networking.private_ip_address - inside the body
# not-testable: private-endpoint.dns.dns_ownership - inherited; decides where the zone id comes from, rendered by the caller
# not-testable: private-endpoint.dns.dns_records - inherited; decides whether a zone group is
# rendered at all (policy: none, the platform's policy writes the record), rendered by the caller
# not-testable: private-endpoint.dns.dns_zone_group - the zone group is a module-internal submodule of the body
# not-testable: private-endpoint.dns.dns_zones - as above
# not-testable: private-endpoint.dns.dns_zone_scope - a data source of the caller
```

A render that must prove the zone group is absent for `left_to_policy` checks the plan JSON
(`terraform show -json`) for a `private_dns_zone_group` submodule, outside `terraform test`.

## Authored rendering

The fallback - and the render for a **manual connection**, which the module does not carry.
Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument |
|---|---|
| the endpoint | `azurerm_private_endpoint` |
| `subnet` | `subnet_id` |
| `target_resource`, `subresource`, `connection_approval` | `private_service_connection { name, private_connection_resource_id, subresource_names, is_manual_connection, request_message }` - `request_message` only when manual |
| `private_ip_address` | `ip_configuration { name, private_ip_address, subresource_name }` |
| the interface name | `custom_network_interface_name` |
| `dns_zone_group: attached` | `private_dns_zone_group { name, private_dns_zone_ids }` |
| `dns_zone_group: left_to_policy` | no `private_dns_zone_group` block - and `lifecycle { ignore_changes = [private_dns_zone_group] }` where the platform policy adds one afterwards, so the plan does not remove it |

Validated against `azurerm` 5.x.
