# Rendering a storage account as Terraform

Mapping from the question set to `azurerm`. General file layout, variable and tagging
conventions are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

Verify argument names against the installed provider rather than this file where they
disagree — `azurerm` renames arguments across major versions, and the examples below are
written for 5.x (verified against 5.10):

```bash
terraform providers schema -json \
  | jq '.provider_schemas["registry.terraform.io/hashicorp/azurerm"].resource_schemas.azurerm_storage_account.block.attributes | keys'
```

## With the AVM module

`Azure/avm-res-storage-storageaccount/azurerm` — the primary rendering. Documented against
**v0.10.0** (resolved 2026-10-17); resolve the current version and re-read its README
inputs before rendering, as [avm.md](../../../core/iac-rendering/references/avm.md) says.
Requires `azapi ~> 2.11`, `modtm ~> 0.3`, `random`, Terraform `>= 1.10`, and takes the
resource group as `parent_id`. It does not use `azurerm` at all.

### Decision → module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Deployment-wide inputs, not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| `deployment.private_dns_records: policy` | `private_endpoints_manage_dns_zone_group = false` | Replaces the `lifecycle { ignore_changes }` of the authored render; `deployment` → `true` plus `private_dns_zone_resource_ids` per endpoint |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.10.0: nothing from this question set. `sas_policy`,
`allowed_copy_scope` and `default_to_oauth_authentication` are inputs the question set
has no decision for — leave them unset rather than inventing a default.

### The call

Rendered for a production, ZRS, private storage account with the platform
referenced, `private_dns_records: policy`:

```hcl
data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

data "naming_name" "storage_account" {
  resource = "Azure::Microsoft.Storage/storageAccounts"
}

# One name per sub-resource through the convention's <?SUBNAME;-%s> token, so the
# index stays last: pep-we-prod-invoicing-blob-01.
data "naming_name" "private_endpoint" {
  for_each = toset(var.private_endpoint_subresources)

  resource   = "Azure::Microsoft.Network/privateEndpoints"
  parameters = { subname = each.key }
}

module "storage" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "~> 0.10.0"

  name      = data.naming_name.storage_account.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  account_kind = "StorageV2"
  # decision: storage-account.data_protection.replication - the SKU name carries it;
  # account_tier / account_replication_type are ignored while this is set.
  account_sku_name = "Standard_ZRS"
  # decision: storage-account.data_protection.access_tier
  access_tier = "Hot"

  # decision: storage-account.networking.public_network_access - a bool on the module
  public_network_access_enabled = false
  # Present although public access is off: documents the posture, and the bypass is a
  # recorded decision (storage-account.networking.allow_azure_services_bypass).
  network_rules = {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  # Explicit although several match the module default: a reviewer reads the call,
  # not the module, and a module minor can move a default.
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  # Access is via Entra ID and RBAC; the module itself never uses a key.
  shared_access_key_enabled = false
  sftp_enabled              = false
  # decision: storage-account.data_protection.hierarchical_namespace - set at creation
  is_hns_enabled = false
  # Settable only at creation. The module default is false.
  infrastructure_encryption_enabled = true

  # decision: storage-account.identity.managed_identity - none; `{ system_assigned = true }` for a
  # reach outward (customer-managed key, a role the account needs)
  managed_identities = {}

  blob_properties = {
    versioning_enabled = true
    change_feed        = { enabled = false }
    delete_retention_policy = {
      enabled = true
      days    = 7
    }
    container_delete_retention_policy = {
      enabled = true
      days    = 7
    }
  }

  # One endpoint per sub-resource, into the platform's private-endpoint subnet.
  private_endpoints = {
    for sub in var.private_endpoint_subresources : sub => {
      name               = data.naming_name.private_endpoint[sub].name
      subnet_resource_id = data.azurerm_subnet.private_endpoints.id
      subresource_name   = sub
    }
  }
  # deployment.private_dns_records: policy - the landing zone's DeployIfNotExists policy
  # attaches the privatelink zone and writes the record. false means the module renders
  # no zone group, so there is no second writer.
  private_endpoints_manage_dns_zone_group = false

  # Two targets: the account emits metrics only, the blob service carries the logs.
  diagnostic_settings_storage_account = {
    platform = {
      workspace_resource_id = data.azurerm_log_analytics_workspace.platform.id
      metrics               = [{ category = "AllMetrics" }]
    }
  }
  diagnostic_settings_blob = {
    platform = {
      workspace_resource_id = data.azurerm_log_analytics_workspace.platform.id
      logs                  = [{ category_group = "audit" }]
      metrics               = [{ category = "AllMetrics" }]
    }
  }

  # Data-plane roles on the account. Empty until the consumer is named (spec: open).
  role_assignments = {
    for ra in var.role_assignments : "${ra.principal_id}-${ra.role}" => {
      role_definition_id_or_name = ra.role
      principal_id               = ra.principal_id
    }
  }

  enable_telemetry = true # deployment.module_telemetry: enabled
  tags             = local.tags
}

output "id" { value = module.storage.resource_id }
output "name" { value = module.storage.name }
output "private_endpoints" { value = module.storage.private_endpoints }
```

`storage_use_azuread = true` on the `azurerm` provider stays, for any `azurerm` data-plane
resource the root adds beside the module; the module itself authenticates with Entra ID
regardless.

### Tests

The contract and the markers are unchanged
([avm.md](../../../core/iac-rendering/references/avm.md#tests-with-a-module-in-the-middle)).
`azapi` and `modtm` are mocked beside `azurerm`; the assert target is the module's
`resource` output, whose `body` is what the call passed in. The output is `sensitive`, so
a failing assert shows `(sensitive value)` — the `error_message` names the expected value.
Settled by the first AVM render on v0.10.0:

```hcl
mock_provider "azapi" {}
mock_provider "modtm" {}

run "networking" {
  command = plan

  # decision: storage-account.networking.public_network_access
  assert {
    condition     = module.storage.resource.body.properties.publicNetworkAccess == "Disabled"
    error_message = "Private: the module must send publicNetworkAccess Disabled."
  }

  # decision: storage-account.networking.allow_azure_services_bypass
  assert {
    condition     = module.storage.resource.body.properties.networkAcls.defaultAction == "Deny" && module.storage.resource.body.properties.networkAcls.bypass == "AzureServices"
    error_message = "The ACL documents the posture: default Deny, trusted Azure services bypass."
  }

  # decision: storage-account.networking.private_endpoint_subresources
  assert {
    condition     = length(module.storage.private_endpoints) == 1 && contains(keys(module.storage.private_endpoints), "blob")
    error_message = "One endpoint per listed sub-resource, blob only."
  }

  # deployment.private_dns_records: policy
  assert {
    condition     = module.storage.private_endpoints["blob"].private_dns_zone_group_id == null
    error_message = "private_dns_records: policy - the platform writes the record, not this code."
  }
}
```

Observable through `resource.body` and asserted the same way: `sku.name` (replication),
`properties.accessTier`, `allowSharedKeyAccess`, `minimumTlsVersion`,
`supportsHttpsTrafficOnly`, `allowBlobPublicAccess`,
`encryption.requireInfrastructureEncryption`, `encryption.keySource` (`Microsoft.Storage`
for platform-managed keys), `isSftpEnabled`, `immutableStorageWithVersioning` (`null` for
none); `resource.identity[0].type` for the managed identity; `resource.name` and
`private_endpoints["blob"].name` for the naming test; `resource.parent_id` for the group.

Not observable, marked `# not-testable: <key> - set through the module's <input>; the
module's own tests cover the mapping`: the five `blob_properties` decisions, the three
diagnostic decisions, `role_assignments`, and `private_endpoint_subnet` — all land in
child modules whose bodies no output exposes. Note that `allow_azure_services_bypass`
became testable with the module, where the authored render could not observe it.

## Authored rendering

The fallback — `implementation: authored`, a repository that already renders the account
this way, or reading what the module does inside.

## Decision → argument

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

`account_tier` is not a question — it follows from `replication` and `access_tier`. Standard
unless the answers call for premium block blob.

`public_network_access` is a string in 5.x. The 4.x bool `public_network_access_enabled`
still exists and is **deprecated** — the schema marks it, `validate` does not warn. A
repository already on 4.x keeps the bool; do not mix the two on one account.

With `shared_access_key_enabled = false` the **provider** also needs
`storage_use_azuread = true` in its `provider "azurerm"` block, or its own data-plane
reads (blob properties, containers) fail with a 403 after a successful create.

## The account

```hcl
data "naming_name" "storage_account" {
  resource = "Azure::Microsoft.Storage/storageAccounts"
}

resource "azurerm_storage_account" "this" {
  name                = data.naming_name.storage_account.name
  resource_group_name = var.resource_group_name
  location            = var.location

  account_tier             = "Standard"
  account_kind             = "StorageV2"
  account_replication_type = "ZRS"
  access_tier              = "Hot"

  # Explicit although several match the provider default: a reviewer can see a
  # decision that was made, and a provider major version cannot move it.
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access           = "Disabled"

  # Access is via Entra ID and RBAC. A key would bypass both and is not
  # attributable in the audit log.
  shared_access_key_enabled = false
  sftp_enabled              = false
  is_hns_enabled            = false

  # Settable only at creation — changing it later replaces the account.
  infrastructure_encryption_enabled = true

  # decision: storage-account.identity.managed_identity - none: no identity block;
  # `identity { type = "SystemAssigned" }` for a reach outward

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = false

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = local.tags
}
```

### The `network_rules` trap

`network_rules` is a nested block on the account *and* also available as the standalone
`azurerm_storage_account_network_rules` resource. Using both for one account produces a
permanent diff, each fighting the other on every plan. Pick the nested block for a new
account; the standalone resource exists for breaking a dependency cycle where a subnet
rule must be added after something the account itself is needed for.

Render it only when `public_network_access` is not `disabled` — with public access off the
ACL has nothing to filter:

```hcl
dynamic "network_rules" {
  for_each = var.public_network_access == "disabled" ? [] : [1]

  content {
    default_action             = var.public_network_access == "enabled" ? "Allow" : "Deny"
    bypass                     = var.allow_azure_services_bypass ? ["AzureServices"] : ["None"]
    ip_rules                   = var.firewall_ip_rules
    virtual_network_subnet_ids = var.firewall_subnet_rules
  }
}
```

`bypass` must be `["None"]` rather than `[]` when the bypass is off — an empty list is not
the same thing to the API.

## Private endpoint

One endpoint per sub-resource, in `res.storage.network.tf`. The DNS zone is referenced, never
created:

```hcl
# One name per sub-resource through the convention's <?SUBNAME;-%s> token, so
# the index stays last: pep-we-prod-invoicing-blob-01. Appending the sub-resource
# to a finished name puts it after the index, and the Bicep render of the same
# spec then names the endpoint differently.
data "naming_name" "private_endpoint" {
  for_each = toset(var.private_endpoint_subresources)

  resource   = "Azure::Microsoft.Network/privateEndpoints"
  parameters = { subname = each.key }
}

resource "azurerm_private_endpoint" "storage" {
  for_each = toset(var.private_endpoint_subresources)

  name                = data.naming_name.private_endpoint[each.key].name
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-${each.key}"
    private_connection_resource_id = azurerm_storage_account.this.id
    subresource_names              = [each.key]
    is_manual_connection           = false
  }

  # Only with deployment.private_dns_records: deployment. Under `policy` - the
  # landing-zone default - a DeployIfNotExists policy writes the record, and a
  # zone group here would be a second writer: drift on every plan.
  dynamic "private_dns_zone_group" {
    for_each = var.private_dns_records == "deployment" ? [1] : []
    content {
      name                 = "default"
      private_dns_zone_ids = [var.private_dns_zone_ids[each.key]]
    }
  }

  # Under `policy`: the zone group the policy attaches would otherwise show up
  # as a change Terraform wants to remove on every plan.
  lifecycle {
    ignore_changes = [private_dns_zone_group]
  }

  tags = local.tags
}
```

When the spec fixes `private_dns_records` (it always does — it is a deployment decision,
not a variable), render only the branch that applies: under `policy` no `dynamic` block and
no `private_dns_zone_ids` variable, just the `lifecycle` block with its comment. A
variable the caller can never meaningfully set is a question the interview already
answered.

`subnet_id` comes from `data.azurerm_subnet.private_endpoints.id` when the network is
referenced (`network_ownership: reference`), and from the deployment's own
`azurerm_subnet` resource when it is created — never from a hardcoded id.

`subresource_names` takes exactly one entry per endpoint. Passing several is accepted at
plan time and fails at apply.

## Role assignments

Scoped to the container where possible, never to the subscription:

```hcl
resource "azurerm_role_assignment" "data" {
  for_each = { for ra in var.role_assignments : "${ra.principal_id}-${ra.role}" => ra }

  scope                = coalesce(each.value.scope, azurerm_storage_account.this.id)
  role_definition_name = each.value.role
  principal_id         = each.value.principal_id
}
```

Use the data-plane roles — `Storage Blob Data Reader`, `Storage Blob Data Contributor`.
`Contributor` and `Owner` are control-plane roles and grant no data access at all, which is
a confusion worth catching in review: an application given `Contributor` on a storage
account still cannot read a blob.

## Customer-managed keys

Only when `key_management: customer_managed`. With a system-assigned identity the
dependency is circular — the identity does not exist until the account does — so either use
a user-assigned identity, or create the account with platform keys and apply
`azurerm_storage_account_customer_managed_key` afterwards:

```hcl
resource "azurerm_storage_account_customer_managed_key" "this" {
  storage_account_id        = azurerm_storage_account.this.id
  key_vault_key_id          = var.cmk_key_vault_key_id
  user_assigned_identity_id = var.user_assigned_identity_id
}
```

Prefer the user-assigned identity. It removes the cycle, and the wrap/unwrap grant can be
in place before the account exists.

## Diagnostics

Two settings, because the account and its blob service are two diagnostic targets. The
account itself emits **no log categories** — a setting on the account with an
`enabled_log` block is rejected at apply. `diagnostic_categories` therefore renders on the
blob service; the account gets metrics only:

```hcl
resource "azurerm_monitor_diagnostic_setting" "storage" {
  name                       = "diag"
  target_resource_id         = azurerm_storage_account.this.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.platform.id

  enabled_metric {
    category = "AllMetrics"
  }
}

# Blob data-plane logs attach to <account>/blobServices/default. A setting on
# the account alone collects no StorageRead/Write/Delete while looking configured.
resource "azurerm_monitor_diagnostic_setting" "storage_blob" {
  name                       = "diag"
  target_resource_id         = "${azurerm_storage_account.this.id}/blobServices/default"
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.platform.id

  dynamic "enabled_log" {
    for_each = toset(var.diagnostic_categories)
    content {
      category_group = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
```

One more pair per sub-resource that has an endpoint and is used (`fileServices`,
`queueServices`, `tableServices`) — a service nobody writes to needs no log.

The workspace id is the referenced workspace's id variable from the stage files
(`observability_ownership: reference`) or the deployment's own workspace module output - never
a data source, and never a literal id in the configuration.

## Tests

Every decision in the question set, one assert each, named by its spec key path; one
`run` per group. The platform's ids are test variables and the remaining data sources are
mocked, so the plan needs no credentials — how, and why the ids must parse, is in
[terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md#tests).
The values below are the defaults; a spec that departs changes the expected value, never
the assert.

```hcl
run "naming" {
  command = plan

  # The naming provider is not mocked: the name is asserted as it will be
  # deployed, which is also the test that catches an edited naming.yaml.
  assert {
    condition     = azurerm_storage_account.this.name == "stweprodinvoicing01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }

  assert {
    condition     = azurerm_private_endpoint.storage["blob"].name == "pep-we-prod-invoicing-blob-01"
    error_message = "Private endpoint name: <?SUBNAME> before the index."
  }
}

run "networking" {
  command = plan

  # decision: storage-account.networking.public_network_access
  assert {
    condition     = azurerm_storage_account.this.public_network_access == "Disabled" && length(azurerm_storage_account.this.network_rules) == 0
    error_message = "Private: no public endpoint, and no ACL that would suggest one."
  }

  # decision: storage-account.networking.private_endpoint_subnet
  assert {
    condition     = azurerm_private_endpoint.storage["blob"].subnet_id == data.azurerm_subnet.private_endpoints.id
    error_message = "The endpoint goes into the deployment's private-endpoint subnet."
  }

  # decision: storage-account.networking.private_endpoint_subresources
  assert {
    condition     = length(azurerm_private_endpoint.storage) == 1 && azurerm_private_endpoint.storage["blob"].private_service_connection[0].subresource_names[0] == "blob"
    error_message = "One endpoint per listed sub-resource, blob only."
  }

  # not-testable: storage-account.networking.allow_azure_services_bypass - network_rules
  # is not rendered with public access disabled; nothing in the plan carries the bypass

  # deployment.private_dns_records: policy
  assert {
    condition     = length(azurerm_private_endpoint.storage["blob"].private_dns_zone_group) == 0
    error_message = "private_dns_records: policy - the platform writes the record, not this code."
  }
}

run "identity" {
  command = plan

  # decision: storage-account.identity.managed_identity
  assert {
    condition     = length(azurerm_storage_account.this.identity) == 0
    error_message = "No identity of its own."
  }

  # decision: storage-account.identity.role_assignments
  assert {
    condition     = length(azurerm_role_assignment.data) == 0
    error_message = "No consumer named yet, so no assignment - open in the spec."
  }
}

run "security" {
  command = plan

  # decision: storage-account.security.shared_access_key_enabled
  assert {
    condition     = azurerm_storage_account.this.shared_access_key_enabled == false
    error_message = "Shared key auth must stay off; access is via Entra ID and RBAC."
  }

  # decision: storage-account.security.min_tls_version
  assert {
    condition     = azurerm_storage_account.this.min_tls_version == "TLS1_2"
    error_message = "TLS 1.2 is the floor."
  }

  # decision: storage-account.security.https_traffic_only
  assert {
    condition     = azurerm_storage_account.this.https_traffic_only_enabled == true
    error_message = "No plain HTTP."
  }

  # decision: storage-account.security.allow_blob_public_access
  assert {
    condition     = azurerm_storage_account.this.allow_nested_items_to_be_public == false
    error_message = "Anonymous container access must not be possible at the account level."
  }

  # decision: storage-account.security.infrastructure_encryption_enabled
  assert {
    condition     = azurerm_storage_account.this.infrastructure_encryption_enabled == true
    error_message = "Settable only at creation; must be on."
  }

  # decision: storage-account.security.key_management
  assert {
    condition     = length(azurerm_storage_account.this.customer_managed_key) == 0
    error_message = "Platform-managed keys: no CMK block."
  }

  # decision: storage-account.security.sftp_enabled
  assert {
    condition     = azurerm_storage_account.this.sftp_enabled == false
    error_message = "SFTP brings local users - credentials outside Entra ID."
  }

  # decision: storage-account.data_protection.hierarchical_namespace
  assert {
    condition     = azurerm_storage_account.this.is_hns_enabled == false
    error_message = "Plain blob storage: no hierarchical namespace unless the account is a data lake."
  }
}

run "data_protection" {
  command = plan

  # decision: storage-account.data_protection.replication
  assert {
    condition     = azurerm_storage_account.this.account_replication_type == "ZRS"
    error_message = "ZRS: survives a zone loss at roughly LRS cost."
  }

  # decision: storage-account.data_protection.access_tier
  assert {
    condition     = azurerm_storage_account.this.access_tier == "Hot"
    error_message = "Hot tier by default."
  }

  # decision: storage-account.data_protection.blob_soft_delete_days
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].delete_retention_policy[0].days == 7
    error_message = "Blob soft delete 7 days."
  }

  # decision: storage-account.data_protection.container_soft_delete_days
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].container_delete_retention_policy[0].days == 7
    error_message = "Container soft delete 7 days."
  }

  # decision: storage-account.data_protection.versioning_enabled
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].versioning_enabled == true
    error_message = "Versioning on: protects against overwrite, which soft delete does not."
  }

  # decision: storage-account.data_protection.change_feed_enabled
  assert {
    condition     = azurerm_storage_account.this.blob_properties[0].change_feed_enabled == false
    error_message = "Change feed off unless something consumes it."
  }

  # decision: storage-account.data_protection.point_in_time_restore_days
  assert {
    condition     = length(azurerm_storage_account.this.blob_properties[0].restore_policy) == 0
    error_message = "Point-in-time restore off: no restore_policy block."
  }

  # decision: storage-account.data_protection.immutability
  assert {
    condition     = length(azurerm_storage_account.this.immutability_policy) == 0
    error_message = "No WORM policy unless a mandate names one."
  }
}

run "observability" {
  command = plan

  # decision: storage-account.observability.diagnostic_workspace
  assert {
    condition     = azurerm_monitor_diagnostic_setting.storage.log_analytics_workspace_id == data.azurerm_log_analytics_workspace.platform.id && azurerm_monitor_diagnostic_setting.storage_blob.log_analytics_workspace_id == data.azurerm_log_analytics_workspace.platform.id
    error_message = "Both settings route to the deployment's workspace."
  }

  # decision: storage-account.observability.diagnostic_categories
  assert {
    condition     = length(azurerm_monitor_diagnostic_setting.storage_blob.enabled_log) == 1 && contains([for l in azurerm_monitor_diagnostic_setting.storage_blob.enabled_log : l.category_group], "audit")
    error_message = "audit on the blob service, and nothing else in production."
  }

  # decision: storage-account.observability.metrics_enabled
  assert {
    condition     = length(azurerm_monitor_diagnostic_setting.storage.enabled_metric) == 1 && length(azurerm_monitor_diagnostic_setting.storage_blob.enabled_metric) == 1
    error_message = "AllMetrics on both targets."
  }
}
```

A decision asserted through a block is indexed: `blob_properties[0]`,
`identity[0]`. A decision rendered as an absent block is `length(...) == 0`.
`enabled_log` is a set — collect it with a `for` and `contains()` rather than comparing
it to a list literal, which never equals a tuple.
