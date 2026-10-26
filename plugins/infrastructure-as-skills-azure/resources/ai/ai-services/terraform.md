# Rendering a single-service AI account as Terraform

Mapping from the question set to the account. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
The module is the one of the [Foundry](../foundry/terraform.md) reference; read it first, only
what differs is here.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-cognitiveservices-account/azurerm` | **v0.11.1** | 2026-10-26 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.11.0`.

**AzAPI-based, and still `azurerm`-constrained.** It takes `parent_id` (the resource group's
id) and requires `azapi ~> 2.5`, `modtm ~> 0.3`, `random`, `time ~> 0.10`, Terraform `>= 1.9`
- and `azurerm >= 4.17.0, < 5.0`, so **a root calling it cannot be on 5.x**.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `kind` | `kind` | One of the eight; the module accepts every Cognitive Services kind, the set narrows it |
| `sku_name` | `sku_name` | `S0` or `F0`; **required** by the module |
| (derived from the name) | `custom_subdomain_name` | **Required** for a firewall, private endpoints and token auth; default `null`; written. Fixed at creation |
| `public_network_access` | `public_network_access_enabled` | **Bool**; module default **`true`** |
| `ip_rules` | `network_acls = { default_action = "Deny", ip_rules, bypass }` | Needs `custom_subdomain_name`; `null` with `disabled` |
| `restrict_outbound` | `outbound_network_access_restricted` | Default `null` (off); written |
| `allowed_fqdns` | `fqdns` | Only with `restrict_outbound`; the host names, no wildcards |
| `private_endpoint_subnet` | `private_endpoints = { account = { subnet_resource_id } }` | One zone, `privatelink.cognitiveservices.azure.com` |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | |
| `role_assignments` | `role_assignments` | The per-kind roles by name |
| `local_authentication_disabled` | `local_auth_enabled` | **Inverse**; default `null` (on); written |
| `key_management`, `cmk_key_vault_key_id` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | Unversioned; `is_hsm_key` beside it for `key_protection: hsm` |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories, log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

Not used here: `cognitive_deployments`, `allow_project_management`, `associated_projects`,
`default_project`, `network_injections` - the Foundry inputs; a single-service account has
none of them.

### The call

```hcl
module "speech" {
  source  = "Azure/avm-res-cognitiveservices-account/azurerm"
  version = "~> 0.11.0"

  name      = data.naming_name.speech.name
  location  = var.location
  parent_id = data.azurerm_resource_group.this.id

  kind     = "SpeechServices" # decision: ai-services.account.kind
  sku_name = "S0"             # decision: ai-services.account.sku_name
  # the hostname - required for the firewall, private endpoints and token auth
  custom_subdomain_name = data.naming_name.speech.name

  # decision: ai-services.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false
  network_acls                  = null
  # decision: ai-services.networking.restrict_outbound, allowed_fqdns
  outbound_network_access_restricted = true
  fqdns                              = []
  private_endpoints = {
    account = {
      name               = data.naming_name.speech_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  managed_identities = { system_assigned = true }

  # decision: ai-services.security.local_authentication_disabled - inverse input
  local_auth_enabled = false

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["Audit", "RequestResponse"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.speech.resource_id }
```

The naming data source uses the kind's identifier
(`Azure::Microsoft.CognitiveServices/accounts::SpeechServices`, abbreviation `spch`); the other
kinds have theirs in `naming.default.yaml`.

### Tests

As for Foundry: with `azapi` and `modtm` mocked, the module's `resource` output echoes the
account under the `azurerm` spelling, so asserts target `module.speech.resource.kind`,
`.sku_name`, `.public_network_access` (or `public_network_access_enabled`),
`.local_authentication_enabled`, `.outbound_network_access_restricted`,
`.custom_subdomain_name` - the exact names read off a first `terraform test` on the pinned
version. The private endpoint, role assignments and the diagnostic setting are children and
`# not-testable:` with a reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x** (`azurerm_cognitive_account`); check against
`terraform providers schema -json`.

| Decision | Argument |
|---|---|
| `kind`, `sku_name`, subdomain | `kind`, `sku_name`, `custom_subdomain_name` |
| `public_network_access`, `ip_rules` | `public_network_access_enabled`, `network_acls { default_action, ip_rules, bypass }` |
| `restrict_outbound`, `allowed_fqdns` | `outbound_network_access_restricted`, `fqdns` |
| `managed_identity` | `identity { type, identity_ids }` |
| `local_authentication_disabled` | `local_auth_enabled` (inverse) |
| `key_management` | `customer_managed_key { key_vault_key_id, identity_client_id }` |
| private endpoint | `azurerm_private_endpoint` with `subresource_names = ["account"]` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
