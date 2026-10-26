# Rendering Communication Services as Terraform

Mapping from the question set to the resources. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## Modules

| | Module | Documented against | Resolved | Status |
|---|---|---|---|---|
| Communication service | **none in the index** (2026-10-26) | - | 2026-10-26 | - |
| Email service + domain + sender | `Azure/avm-res-communication-emailservice/azurerm` | **v0.3.0** | 2026-10-26 | Available |

The communication resource itself has no AVM Terraform module, so **the authored path is the
primary** for it; the e-mail service (with `email` not `none`) is the module. Resolve the current
version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.3.0`.

**Provider requirements.** The e-mail module is AzAPI-based (`parent_id`, `azapi ~> 2.12`,
`modtm ~> 0.3`, `random ~> 3.7`, Terraform `>= 1.11`) and needs no `azurerm`. The communication
resource is rendered as an `azapi_resource` too, because **`azurerm_communication_service` (5.x)
has no argument for `disableLocalAuth` or `publicNetworkAccess`** - it takes `data_location`
and `tags` only. The root keeps `azurerm` for the diagnostic setting and the platform data
sources.

### Decision -> input

| Decision | Where | Input | Note |
|---|---|---|---|
| `location` | both | `location = "global"` | Literal |
| `data_location` | both | `body.properties.dataLocation` / `data_location` | Immutable; the e-mail service must match |
| `email` | module | the module call exists, with `email_communication_service_domains = { <k> = { name, domain_management } }` | `AzureManaged` with name `AzureManagedDomain`; `CustomerManaged` with the domain name |
| `custom_domain_name` | module | `email_communication_service_domains.<k>.name` | |
| `sender_usernames` | module | `email_communication_service_domain_sender_usernames = { <k> = { name, email_communication_service_domain_name_key, display_name } }` | |
| `user_engagement_tracking` | module | `email_communication_service_domains.<k>.user_engagement_tracking_enabled` | Default `false`; written |
| (linking) | authored | `body.properties.linkedDomains = ["<email service id>/domains/<name>"]` | The domain id, not the service id |
| `public_network_access` | authored | `body.properties.publicNetworkAccess` | `Enabled` / `Disabled` / `SecuredByPerimeter`; forced to `Enabled` without a perimeter |
| `network_security_perimeter` | authored | `azapi_resource` `Microsoft.Network/networkSecurityPerimeters/profiles/resourceAssociations` | Only when set |
| `managed_identity`, `user_assigned_identity_ids` | authored | `identity { type, identity_ids }` | |
| `role_assignments` | authored / module | `azurerm_role_assignment` on the communication resource; `role_assignments` on the module | |
| `local_authentication_disabled` | authored | `body.properties.disableLocalAuth` | Not in `azurerm`; written |
| `diagnostic_*`, `metrics_enabled` | authored | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }`, `enabled_metric { category }` | |
| `deployment.module_telemetry` | module | `enable_telemetry` | |
| `context.tags` | both | `tags = local.tags` | |

### The call

```hcl
module "email" {
  source  = "Azure/avm-res-communication-emailservice/azurerm"
  version = "~> 0.3.0"

  name          = "${data.naming_name.communication.name}-email"
  parent_id     = data.azurerm_resource_group.this.id
  location      = "global"
  data_location = "Europe" # decision: communication-services.service.data_location

  # decision: communication-services.service.email, custom_domain_name, user_engagement_tracking
  email_communication_service_domains = {
    managed = {
      name                             = "AzureManagedDomain"
      domain_management                = "AzureManaged"
      user_engagement_tracking_enabled = false
    }
  }
  # decision: communication-services.service.sender_usernames
  email_communication_service_domain_sender_usernames = {
    donotreply = {
      name                                        = "DoNotReply"
      email_communication_service_domain_name_key = "managed"
      display_name                                = "DoNotReply"
    }
  }

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
      principal_type             = v.principal_type
    }
  }
  enable_telemetry = true
  tags             = local.tags
}

resource "azapi_resource" "communication" {
  type      = "Microsoft.Communication/communicationServices@2025-09-01"
  name      = data.naming_name.communication.name
  parent_id = data.azurerm_resource_group.this.id
  location  = "global"
  tags      = local.tags

  # decision: communication-services.identity.managed_identity - none: no identity block;
  # `identity { type = "SystemAssigned" }` for recordings in storage

  body = {
    properties = {
      dataLocation = "Europe" # decision: communication-services.service.data_location
      # decision: communication-services.security.local_authentication_disabled
      disableLocalAuth = true
      # decision: communication-services.networking.public_network_access - forced to Enabled
      # without a network security perimeter; the resource has no private endpoint
      publicNetworkAccess = "Enabled"
      linkedDomains       = ["${module.email.resource_id}/domains/AzureManagedDomain"]
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "communication" {
  name                       = "diag"
  target_resource_id         = azapi_resource.communication.id
  log_analytics_workspace_id = var.diagnostic_workspace_id
  # decision: communication-services.observability.diagnostic_categories
  enabled_log { category = "Usage" }
  enabled_log { category = "AuthOperational" }
  enabled_metric { category = "AllMetrics" }
}

output "id" { value = azapi_resource.communication.id }
```

For `email: custom_domain` the domain entry is `name = var.custom_domain_name`,
`domain_management = "CustomerManaged"`, and the module's domain output carries the verification
records (`verificationRecords`: Domain, SPF, DKIM, DKIM2, DMARC) that the handover lists for the
DNS owner. `2025-09-01` is the API version the Bicep AVM module targets and the first with
`disableLocalAuth` and `publicNetworkAccess`; check `az provider show -n Microsoft.Communication`
and the pinned `azapi` before moving it.

### Tests

With `azapi` and `modtm` mocked, the communication resource is a root-level `azapi_resource`,
so every property above is asserted on `azapi_resource.communication.body.properties.*` at plan
time, and `identity[0].type`. The e-mail module exposes `resource_id` and `resource`; what the
domain children expose is read off a first `terraform test` on the pinned version, otherwise
`sender_usernames` and `user_engagement_tracking` are `# not-testable:` with a reason. The
diagnostic setting is a root resource and is asserted directly.

## Authored rendering

The fallback for the e-mail side, and the `azurerm` form where a repository already uses it.
Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource / argument |
|---|---|
| `data_location` | `azurerm_communication_service.data_location`, `azurerm_email_communication_service.data_location` |
| `email`, `custom_domain_name`, `user_engagement_tracking` | `azurerm_email_communication_service_domain` (`domain_management`, `user_engagement_tracking_enabled`) |
| `sender_usernames` | `azurerm_email_communication_service_domain_sender_username` |
| `local_authentication_disabled`, `public_network_access`, linking, identity | **not in `azurerm`** - an `azapi_update_resource` on the communication service, or the `azapi_resource` above |
| diagnostics | `azurerm_monitor_diagnostic_setting` |
