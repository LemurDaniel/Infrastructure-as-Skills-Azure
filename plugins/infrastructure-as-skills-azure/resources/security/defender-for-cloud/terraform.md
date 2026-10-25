# Rendering Defender for Cloud as Terraform

Mapping from the question set to the subscription's plans and contact. General layout, variables
and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).
Nothing here renders when `defender_ownership` is `platform`.

## With the AVM module

**There is none.** The AVM index has no Terraform module for Defender for Cloud (`Microsoft.Security/pricings`)
- neither a resource nor a pattern module (looked up 2026-10-25, in the same index as
[avm.md](../../../core/iac-rendering/references/avm.md)). It is treated as `Proposed`: the render is
authored, with `implementation: authored` and `source: forced`, `forced_by: no AVM module for
Microsoft.Security/pricings`. The Bicep side has a pattern module (see `bicep.md`).

## Authored rendering

Targets `azurerm` **5.x** (checked against `terraform providers schema -json`, 5.11.0) and `azapi`.
`azurerm_security_center_auto_provisioning`, the resource for the retired agent setting, no longer
exists in 5.x and is not rendered.

| Decision | Resource and argument |
|---|---|
| `plans` | one `azurerm_security_center_subscription_pricing` per entry: `resource_type = <plan>`, `tier = "Standard"` |
| `servers_plan` | `subplan` on the `VirtualMachines` pricing (`P1`, `P2`) |
| (storage) | `subplan = "DefenderForStorageV2"` on the `StorageAccounts` pricing |
| `storage_malware_scanning`, `storage_malware_scan_cap_gb` | `extension { name = "OnUploadMalwareScanning", additional_extension_properties = { CapGBPerMonth = "<n>" } }` |
| `storage_sensitive_data_discovery` | `extension { name = "SensitiveDataDiscovery" }` |
| `security_contact_emails`, `notify_subscription_owners`, `alert_minimum_severity` | `azapi_resource` `Microsoft.Security/securityContacts@2023-12-01-preview`, name `default` |
| `subscription_id` | the provider's `subscription_id`, a root variable |
| `defender_ownership` | whether the resources exist at all (`count` / the module call) |

```hcl
variable "plans" {
  type = list(string)
}

locals {
  plan_subplan = {
    VirtualMachines = var.servers_plan             # decision: defender-for-cloud.security.servers_plan
    StorageAccounts = "DefenderForStorageV2"
  }
  storage_extensions = {
    OnUploadMalwareScanning = {
      enabled = var.storage_malware_scanning       # decision: ...storage_malware_scanning
      props   = { CapGBPerMonth = tostring(var.storage_malware_scan_cap_gb) }
    }
    SensitiveDataDiscovery = {
      enabled = var.storage_sensitive_data_discovery
      props   = {}
    }
  }
}

# decision: defender-for-cloud.security.plans - one paid plan per entry; unlisted plans are not touched
resource "azurerm_security_center_subscription_pricing" "plan" {
  for_each = toset(var.plans)

  resource_type = each.key
  tier          = "Standard"
  subplan       = lookup(local.plan_subplan, each.key, null)

  dynamic "extension" {
    for_each = each.key == "StorageAccounts" ? { for k, v in local.storage_extensions : k => v if v.enabled } : {}
    content {
      name                            = extension.key
      additional_extension_properties = length(extension.value.props) == 0 ? null : extension.value.props
    }
  }
}

# decision: defender-for-cloud.identity.* - azapi, because azurerm_security_center_contact has no
# severity threshold and no role-based recipients
resource "azapi_resource" "security_contact" {
  type      = "Microsoft.Security/securityContacts@2023-12-01-preview"
  name      = "default"
  parent_id = "/subscriptions/${var.subscription_id}"
  body = {
    properties = {
      emails               = join(";", var.security_contact_emails)
      isEnabled            = true
      notificationsByRole  = { state = var.notify_subscription_owners ? "On" : "Off", roles = ["Owner"] }
      notificationsSources = [{ sourceType = "Alert", minimalSeverity = var.alert_minimum_severity }]
    }
  }
}
```

The `azurerm` provider in this root is configured for the stage's subscription
(`subscription_id = var.subscription_id`); the plans are written there. `emails` is a
semicolon-separated string in the API. The `azurerm` contact resource
(`azurerm_security_center_contact`: `email`, `alert_notifications`, `alerts_to_admins`) is the
older alternative for a repository that already uses it; it cannot express the severity
decision.

`azurerm_security_center_subscription_pricing` writes `Free` back on destroy: the resource owns the
setting. `extension` blocks name an extension and enable it by being present; an extension that is
off is absent, not `isEnabled = false`.

### Tests

`mock_provider "azurerm"` and `mock_provider "azapi"` keep the plan credential-free. Asserts target
`azurerm_security_center_subscription_pricing.plan["<plan>"]` (`tier`, `subplan`, the
extensions) and the `azapi_resource.security_contact` body (emails, severity, role-based
notification). The meaning of a plan on a live subscription - what is billed - is
`# not-testable:` with that reason.
