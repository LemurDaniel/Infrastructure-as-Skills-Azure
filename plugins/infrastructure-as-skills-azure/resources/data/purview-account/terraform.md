# Rendering a Microsoft Purview account as Terraform

Mapping from the question set to the account. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-purview-account/azurerm` | none in the index | 2026-10-26 | **Proposed** - not published to the registry |

The index lists the module as `Proposed` with no release, and the registry has no versions. Per
[avm.md](../../../core/iac-rendering/references/avm.md) a module that is not `Available` is not
used: **the authored rendering below is the primary** on this target. Re-check the index before a
render; when it becomes `Available`, this reference is re-walked against its inputs.

## Authored rendering

Targets `azurerm` **5.x** (`azurerm_purview_account`, API `2021-12-01`), with `azapi ~> 2.4` for the
one property the provider does not expose. Check arguments against `terraform providers schema -json`
for the version the root pins. `ownership: platform` renders an id variable from the stage files - never a
data source ([terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md#referencing-what-the-deployment-does-not-own)) - and nothing below.

### Decision -> resource and argument

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Resource and argument | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | no `private_dns_zone_group` block | |
| `deployment.resource_lock` | `azurerm_management_lock` (`CanNotDelete`) on the account | A lost account is a lost data map |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
# no AVM Terraform module (Proposed, unpublished): authored on azurerm 5.x
resource "azurerm_purview_account" "this" {
  name                = data.naming_name.pview.name
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tags

  # decision: purview-account.account.managed_resource_group_name - the service default
  managed_resource_group_name = "managed-rg-${data.naming_name.pview.name}"
  # decision: purview-account.account.managed_event_hub - the provider default is true
  managed_event_hub_enabled = false
  # decision: purview-account.networking.public_network_access - the provider default is true
  public_network_enabled = false

  # decision: purview-account.identity.managed_identity - system-assigned is mandatory
  identity {
    type = "SystemAssigned"
  }
}

# decision: purview-account.account.managed_resources_public_access - no azurerm argument
resource "azapi_update_resource" "managed_resources_public_access" {
  type        = "Microsoft.Purview/accounts@2021-12-01"
  resource_id = azurerm_purview_account.this.id
  body = {
    properties = { managedResourcesPublicNetworkAccess = "Disabled" }
  }
}

# decision: purview-account.networking.private_endpoint_subnet / private_endpoint_subresources
locals {
  account_endpoints = {
    account = azurerm_purview_account.this.id
    portal  = azurerm_purview_account.this.id
    blob    = azurerm_purview_account.this.managed_resources[0].storage_account_id
    queue   = azurerm_purview_account.this.managed_resources[0].storage_account_id
  }
}

resource "azurerm_private_endpoint" "this" {
  for_each            = local.account_endpoints
  name                = "pep-${data.naming_name.pview.name}-${each.key}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = local.tags

  private_service_connection {
    name                           = each.key
    private_connection_resource_id = each.value
    subresource_names              = [each.key]
    is_manual_connection           = false
  }
  # private_dns_records: policy - no private_dns_zone_group, the platform policy writes the record
}

# decision: purview-account.observability.diagnostic_workspace / diagnostic_categories / metrics_enabled
resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "diag"
  target_resource_id         = azurerm_purview_account.this.id
  log_analytics_workspace_id = var.diagnostic_workspace_id

  enabled_log { category = "ScanStatusLogEvent" }
  enabled_log { category = "DataSensitivityLogEvent" }
  enabled_log { category = "Security" }

  enabled_metric { category = "AllMetrics" }
}

output "id" { value = azurerm_purview_account.this.id }
output "principal_id" { value = azurerm_purview_account.this.identity[0].principal_id }
```

Validated with `terraform validate` against `azurerm` 5.11.0 and `azapi` 2.x. With
`managed_event_hub: true` the map gains `namespace = azurerm_purview_account.this.managed_resources[0].event_hub_namespace_id`
(sub-resource `namespace`); `role_assignments` are `azurerm_role_assignment` with
`scope = azurerm_purview_account.this.id` and the role by name; the lock is an
`azurerm_management_lock` in the stages `resource_lock` names.

### Collection roles

The root collection's roles are granted against the account's metadata policy API
(`PUT /policystore/metadataPolicies/{id}` on `https://<name>.purview.azure.com`, API version
`2021-07-01`) by a step after the apply, run as a Collection admin - the deploying principal is one
by creation. The spec records `collection_roles` as that step; no provider resource exists for it.

### Tests

With `azurerm` and `azapi` mocked, every argument above is a root resource and observable in the
plan: `public_network_enabled`, `managed_event_hub_enabled`, `managed_resource_group_name`, the
identity type, the `azapi_update_resource` body, each endpoint's `subresource_names`, and the
diagnostic setting's categories. The managed storage account id is unknown at plan time
(`managed_resources` is computed), so the `blob` and `queue` endpoints' target is asserted as
present, not by value, with a `# not-testable:` comment saying so. `collection_roles` and the
platform's reference under `ownership: platform` are `# not-testable:` (not a resource of this
plan).
