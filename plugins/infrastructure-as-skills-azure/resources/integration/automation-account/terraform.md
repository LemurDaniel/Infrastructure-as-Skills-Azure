# Rendering an automation account as Terraform

Mapping from the question set to the automation account. General layout, variables and tagging
are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-automation-automationaccount/azurerm` | **v0.3.0** | 2026-11-01 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**`azurerm`-based**: the account is an `azurerm_automation_account` (takes
`resource_group_name`, a name). Requires `azurerm ~> 4.0`, `azapi ~> 2.12`,
`random >= 3.5.0`, Terraform `>= 1.9, < 2.0` - no `modtm`. A root calling it cannot be on
`azurerm` 5.x, and the authored fallback in that root follows the 4.x spelling (the account's
arguments are unchanged in 5.x). The root's provider set is the union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Not decisions of this set:

| Decision | Input | Note |
|---|---|---|
| (the account) | `name` through the naming provider | |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not carried by the module at v0.3.0: nothing from this question set. The `automation_*` inputs
(runbooks, schedules, webhooks, variables, credentials, certificates, connections, modules,
hybrid worker groups, source controls, watchers) are content and stay unset. `lock` stays unset:
`deployment.resource_lock` does not list automation accounts.

### The call

```hcl
data "naming_name" "automation_account" {
  resource = "Azure::Microsoft.Automation/automationAccounts"
}

module "automation_account" {
  source  = "Azure/avm-res-automation-automationaccount/azurerm"
  version = "~> 0.3.0"

  name                = data.naming_name.automation_account.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: automation-account.account.sku
  sku = "Basic"

  # decision: automation-account.networking.public_network_access - disabled renders false
  public_network_access_enabled = false
  # decision: automation-account.security.local_authentication_disabled - inverse: true renders false
  local_authentication_enabled = false

  # decision: automation-account.identity.managed_identity
  managed_identities = {
    user_assigned_resource_ids = [var.user_assigned_identity_id] # decision: automation-account.identity.user_assigned_identity_ids
  }

  # decision: automation-account.security.key_management - customer_managed only; platform_managed leaves it null
  encryption = [{
    key_vault_key_id          = var.cmk_key_vault_key_id # decision: automation-account.security.cmk_key_vault_key_id
    user_assigned_identity_id = var.user_assigned_identity_id
  }]

  # decision: automation-account.networking.private_endpoint_subresources - one entry each
  private_endpoints = {
    webhook = {
      subnet_resource_id = var.private_endpoint_subnet_id # decision: automation-account.networking.private_endpoint_subnet
      subresource_name   = "Webhook"
    }
    dscandhybridworker = {
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "DSCAndHybridWorker"
    }
  }
  private_endpoints_manage_dns_zone_group = false # private_dns_records: policy

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.log_analytics_workspace_id                # decision: automation-account.observability.diagnostic_workspace
      log_categories        = ["JobLogs", "JobStreams", "AuditEvent"]       # decision: automation-account.observability.diagnostic_categories
      log_groups            = []
      metric_categories     = ["AllMetrics"]                               # decision: automation-account.observability.metrics_enabled
    }
  }

  role_assignments = {} # decision: automation-account.identity.role_assignments

  enable_telemetry = false # deployment.module_telemetry: disabled
  tags             = local.tags
}

output "id" { value = module.automation_account.resource_id }
```

Validated with `terraform validate` (registry, v0.3.0, `azurerm` 4.81, `azapi` 2.13).

### Tests

`mock_provider "azurerm"`, `"azapi"` and `"random"`; the naming provider stays real. The module
exposes no `resource` output - only `resource_id`, `automation_account_name`,
`hybrid_service_url`, `private_endpoints` and `system_assigned_mi_principal_id` - so the name and
the endpoints are observable and the account's arguments are not:

```hcl
run "naming" {
  command = plan

  assert {
    condition     = module.automation_account.automation_account_name == "aa-gwc-dev-telemetry-01"
    error_message = "The name must come from naming.yaml, not from a literal."
  }
}

run "networking" {
  command = plan

  # decision: automation-account.networking.private_endpoint_subresources
  assert {
    condition     = length(module.automation_account.private_endpoints) == 2
    error_message = "One endpoint per sub-resource: Webhook and DSCAndHybridWorker."
  }
}

# automation-account.networking.private_endpoint_subnet is asserted with the endpoints: both sit in the endpoint subnet
# not-testable: automation-account.account.sku - the module has no resource output; read from the plan JSON
# not-testable: automation-account.networking.public_network_access - as above
# not-testable: automation-account.security.local_authentication_disabled - as above
# not-testable: automation-account.identity.managed_identity - as above
# not-testable: automation-account.identity.user_assigned_identity_ids - as above
# not-testable: automation-account.security.key_management - as above
# not-testable: automation-account.security.cmk_key_vault_key_id - as above
# not-testable: automation-account.identity.role_assignments - module-internal role assignments; read from the plan JSON
# not-testable: automation-account.observability.diagnostic_workspace - the diagnostic setting is module-internal; read from the plan JSON
# not-testable: automation-account.observability.diagnostic_categories - as above
# not-testable: automation-account.observability.metrics_enabled - as above
```

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.
`azurerm_automation_account` takes `sku_name` (required), `public_network_access_enabled` and
`local_authentication_enabled` (bools, unlike most 5.x resources), an `identity` block and an
`encryption` block (`key_vault_key_id`, `user_assigned_identity_id`). The private endpoints are
`azurerm_private_endpoint`, one per sub-resource; the diagnostics an
`azurerm_monitor_diagnostic_setting`.

What each decision renders to - the resource and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

Checked against the `azurerm` 5.12 schema.
