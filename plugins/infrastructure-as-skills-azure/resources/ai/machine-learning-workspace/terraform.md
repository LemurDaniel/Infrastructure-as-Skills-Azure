# Rendering an Azure Machine Learning workspace as Terraform

Mapping from the question set to the workspace. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-machinelearningservices-workspace/azurerm` | **v0.9.0** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.9.0`.

**AzAPI-based with an `azurerm` constraint**: it takes `resource_group_name` (a name) and
requires `azapi ~> 2.6`, `azurerm >= 4.17.0, < 5.0` - **a root calling it cannot be on 5.x** -
plus `modtm ~> 0.3`, `random`, Terraform `>= 1.9`. It creates the dependent resources itself
when their `resource_id` is null; this set always passes ids, so nothing is created implicitly.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| (kind) | `kind = "Default"` | Module default `Default`; written. `Hub` / `Project` are not this set |
| `storage_account` | `storage_account = { resource_id }` | Null makes the module **create one**; always set |
| `key_vault` | `key_vault = { resource_id }` | As above |
| `application_insights` | `application_insights = { resource_id }` | As above |
| `container_registry` | `container_registry = { resource_id }` | `{ resource_id = null }` when empty |
| `hbi_workspace` | `hbi_workspace` | Default `false`; written |
| `v1_legacy_mode` | - | **Not carried by the module** (`properties.v1LegacyMode`); `_target_overrides` or authored. The platform default is off, which is the set's default |
| `image_build_compute` | `image_build_compute` | `null` when empty |
| `computes` | - | **Not carried by the module**: `azapi_resource` `Microsoft.MachineLearningServices/workspaces/computes` beside it, after the workspace |
| `managed_network_isolation` | `workspace_managed_network = { isolation_mode }` | `AllowOnlyApprovedOutbound` / `AllowInternetOutbound` / `Disabled`; module default **`Disabled`**; written. `spark_ready` defaults `true` |
| `outbound_fqdns` | `workspace_managed_network.outbound_rules.fqdn = { <k> = { destination } }` | The first rule provisions a firewall (`firewall_sku`, default `Standard`) |
| `provision_network_now` | `provision_network_now_enabled` | Default `false`; written |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default `false`. `is_private` is deprecated |
| `ip_allowlist` | `ip_allowlist` | |
| `private_endpoint_subnet` | `private_endpoints = { amlworkspace = { subnet_resource_id } }` | Two zones |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `serverless_compute_no_public_ip` | `serverless_compute = { public_ip_enabled }` | **Inverse**; default `false` = no public IP |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities`, `primary_user_assigned_identity = { resource_id }` | The primary is required with user-assigned |
| `role_assignments` | `role_assignments` | |
| `storage_datastore_auth` | `storage_access_type` | `identity` / `accessKey`; module default `identity`; written. Documented as deprecated with a future API version |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | |
| `service_side_cmk` | `service_side_cmk_encryption_enabled` | Default `false`; written |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "ml_workspace" {
  source  = "Azure/avm-res-machinelearningservices-workspace/azurerm"
  version = "~> 0.9.0"

  name                = data.naming_name.ml_workspace.name
  location            = var.location
  resource_group_name = var.resource_group_name

  kind = "Default"
  # decision: machine-learning-workspace.workspace.storage_account, key_vault, application_insights, container_registry
  storage_account      = { resource_id = var.storage_account_id }
  key_vault            = { resource_id = var.key_vault_id }
  application_insights = { resource_id = var.application_insights_id }
  container_registry   = { resource_id = var.container_registry_id }

  hbi_workspace       = false # decision: machine-learning-workspace.workspace.hbi_workspace
  image_build_compute = null  # decision: machine-learning-workspace.workspace.image_build_compute

  # decision: machine-learning-workspace.networking.managed_network_isolation, outbound_fqdns -
  # the module default is Disabled
  workspace_managed_network = {
    isolation_mode = "AllowOnlyApprovedOutbound"
    spark_ready    = false
    outbound_rules = {
      fqdn = {}
    }
  }
  provision_network_now_enabled = true # decision: machine-learning-workspace.networking.provision_network_now
  # decision: machine-learning-workspace.networking.public_network_access - a bool
  public_network_access_enabled = false
  ip_allowlist                  = []
  private_endpoints = {
    amlworkspace = {
      name               = data.naming_name.ml_workspace_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the records
  private_endpoints_manage_dns_zone_group = false
  # decision: machine-learning-workspace.networking.serverless_compute_no_public_ip - inverse
  serverless_compute = {
    public_ip_enabled = false
  }

  managed_identities = { system_assigned = true }

  # decision: machine-learning-workspace.security.storage_datastore_auth, service_side_cmk
  storage_access_type                 = "identity"
  service_side_cmk_encryption_enabled = false

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
      log_categories        = ["AmlComputeClusterEvent", "AmlComputeJobEvent", "AmlRunStatusChangedEvent", "ModelsChangeEvent", "DataStoreChangeEvent", "ManagedNetworkEvent"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.ml_workspace.resource_id }
```

With `key_management: customer_managed` the call adds `customer_managed_key = { ... }`,
`managed_identities = { user_assigned_resource_ids = [...] }` and
`primary_user_assigned_identity = { resource_id = ... }`, and `service_side_cmk_encryption_enabled = true`.

### Computes and the legacy flag

Neither is a module input. A compute is rendered after the workspace:

```hcl
resource "azapi_resource" "compute" {
  for_each = { for c in var.computes : c.name => c }

  type      = "Microsoft.MachineLearningServices/workspaces/computes@2024-10-01"
  name      = each.key
  parent_id = module.ml_workspace.resource_id
  location  = var.location

  body = {
    properties = {
      computeType = each.value.type # "AmlCompute" or "ComputeInstance"
      properties  = each.value.properties
    }
  }
}
```

`v1_legacy_mode` is written only when `true`, through the module's `_target_overrides` on the
workspace body (`properties.v1LegacyMode`); off is the platform default and is recorded as such.
The API version is one `az provider show -n Microsoft.MachineLearningServices` lists and the
pinned `azapi` knows.

### Tests

With `azapi` and `modtm` mocked, what the module's `resource` output exposes is read off a first
`terraform test` on the pinned version; the workspace is an `azapi_resource`, so expect
`body.properties.*` (`publicNetworkAccess`, `managedNetwork.isolationMode`, `hbiWorkspace`,
`storageAccount`, `keyVault`, `applicationInsights`, `containerRegistry`, `systemDatastoresAuthMode`,
`serverlessComputeSettings`) and `identity[0].type`. The private endpoint, role assignments and
the diagnostic setting are children and `# not-testable:` with a reason; `computes` is asserted
on the authored resource.

## Authored rendering

The fallback. Targets `azurerm` **5.x** (`azurerm_machine_learning_workspace`); check against
`terraform providers schema -json`.

| Decision | Argument |
|---|---|
| dependencies | `storage_account_id`, `key_vault_id`, `application_insights_id`, `container_registry_id` |
| `hbi_workspace` | `high_business_impact` |
| `v1_legacy_mode` | `v1_legacy_mode_enabled` |
| `image_build_compute` | `image_build_compute_name` |
| `managed_network_isolation`, `provision_network_now` | `managed_network { isolation_mode, provision_on_creation_enabled }`; FQDN rules are `azurerm_machine_learning_workspace_network_outbound_rule_fqdn` |
| `public_network_access` | `public_network_access_enabled` |
| `serverless_compute_no_public_ip` | `serverless_compute { public_ip_enabled }` (inverse) |
| `managed_identity` | `identity { type, identity_ids }`, `primary_user_assigned_identity` |
| `storage_datastore_auth` | `storage_account_access_type` (`Identity` / `AccessKey`) |
| `key_management`, `service_side_cmk` | `encryption { key_vault_id, key_id, user_assigned_identity_id }`, `service_side_encryption_enabled` |
| `computes` | `azurerm_machine_learning_compute_cluster`, `azurerm_machine_learning_compute_instance` |
| private endpoint | `azurerm_private_endpoint` with `subresource_names = ["amlworkspace"]` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
