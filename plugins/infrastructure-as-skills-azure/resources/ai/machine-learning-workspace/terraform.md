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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Inputs no decision covers

| Input | Module input | Note |
|---|---|---|
| (kind) | `kind = "Default"` | Module default `Default`; written. `Hub` / `Project` are not this set |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
