# Rendering an Azure Data Factory as Terraform

Mapping from the question set to the factory. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-datafactory-factory/azurerm` | **v0.2.0** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm >= 3.0, < 5.0` - **a
root calling it cannot be on 5.x** - plus `azapi ~> 2.4`, `modtm ~> 0.3`, `random ~> 3.5`, and
Terraform `>= 1.5`. The root's provider set is the union with the other modules in the
deployment. The module builds the factory, `dataFactory` private endpoints, the git binding,
global parameters, self-hosted runtimes, credentials, role assignments and the diagnostic
setting - and a set of linked services and one dataset this plugin never renders (content). It
builds **no** Azure integration runtime, **no** managed private endpoint and **no** `portal`
endpoint.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.resource_lock` | `lock` | Not on the lock list: a factory is recreated from the spec and its repository |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "adf" {
  source  = "Azure/avm-res-datafactory-factory/azurerm"
  version = "~> 0.2.0"

  name                = data.naming_name.adf.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: data-factory.factory.managed_virtual_network - the module default is false
  managed_virtual_network_enabled = true

  # decision: data-factory.factory.self_hosted_integration_runtime - none
  integration_runtime_self_hosted = {}

  # decision: data-factory.factory.global_parameters
  global_parameters = [
    { name = "environment", type = "String", value = var.environment },
  ]

  # decision: data-factory.factory.purview_account - none
  purview_id = null

  # decision: data-factory.source_control.git_provider - github, development stage only
  github_configuration = {
    account_name    = var.git_account
    repository_name = var.git_repository
    branch_name     = "main"
    root_folder     = "/"
  }

  # decision: data-factory.networking.public_network_access - the module default is true
  public_network_enabled = false
  # decision: data-factory.networking.private_endpoint_subnet / private_endpoint_subresources (dataFactory; portal below)
  private_endpoints = {
    dataFactory = {
      name               = data.naming_name.adf_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  private_endpoints_manage_dns_zone_group = false

  # decision: data-factory.identity.managed_identity
  managed_identities = { system_assigned = true }

  # decision: data-factory.security.key_management - platform managed: no customer_managed_key_id

  # decision: data-factory.observability.diagnostic_workspace / diagnostic_categories / metrics_enabled
  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["PipelineRuns", "ActivityRuns", "TriggerRuns"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  # decision: data-factory.identity.role_assignments
  role_assignments = {}

  enable_telemetry = true
  tags             = local.tags
}

# decision: data-factory.factory.managed_virtual_network - the Azure runtime inside it (not an input of the module)
resource "azurerm_data_factory_integration_runtime_azure" "managed" {
  name                    = "AutoResolveIntegrationRuntime"
  data_factory_id         = module.adf.resource_id
  location                = "AutoResolve"
  virtual_network_enabled = true
  time_to_live_min        = 10
}

# decision: data-factory.factory.managed_private_endpoints - one per source
resource "azurerm_data_factory_managed_private_endpoint" "lake" {
  name               = "lake-dfs"
  data_factory_id    = module.adf.resource_id
  target_resource_id = var.lake_storage_account_id
  subresource_name   = "dfs"
}

# decision: data-factory.networking.private_endpoint_subresources - the portal endpoint the module does not create
resource "azurerm_private_endpoint" "portal" {
  name                = data.naming_name.adf_portal_private_endpoint.name
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = local.tags

  private_service_connection {
    name                           = "portal"
    private_connection_resource_id = module.adf.resource_id
    subresource_names              = ["portal"]
    is_manual_connection           = false
  }
}

output "id" { value = module.adf.resource_id }
```

Validated with `terraform validate` against v0.2.0 (azurerm 4.x). The git block is rendered for the
development stage only: `github_configuration = var.environment == "development" ? { ... } : null`,
or the stage's parameter file carries the object and the others `null`. A customer-managed key adds
`customer_managed_key_id = var.cmk_key_id`, `customer_managed_key_identity_id = var.identity_id`
and the identity in `managed_identities`; Azure DevOps replaces `github_configuration` by
`vsts_configuration` with `project_name` and `tenant_id`.

### The runtime key and the source roles

`create_key_only` adds `integration_runtime_self_hosted = { shir = { name = "shir-onprem" } }`; the
key is read after the apply with an `azapi_resource_action` (`listAuthKeys` on the runtime's id)
whose output goes into a Key Vault secret, never into a root output. `source_access` is a
`role_assignments` entry on each source's module with
`principal_id = module.adf.resource.identity[0].principal_id` - rendered beside the source, not
here. Managed private endpoint connections are approved on the source
(`az network private-endpoint-connection approve`) by the pipeline where this deployment owns it.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's `resource` output (the
`azurerm_data_factory` attributes echoed from the inputs): `public_network_enabled`,
`managed_virtual_network_enabled`, `github_configuration`, `global_parameter`, `purview_id`,
`customer_managed_key_id`, the identity type. The authored runtime, managed private endpoint and
portal endpoint are root resources and fully observable (`virtual_network_enabled`,
`subresource_name`, `subresource_names`). The output paths are read off a first `terraform test`
run on the pinned version, not recalled. The module's `dataFactory` endpoint, diagnostic setting
and role assignments are built in children: `# not-testable:` with that reason. `source_access`,
the endpoint approvals and the runtime key are `# not-testable:` (not a resource of this plan).

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the factory this
way. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
