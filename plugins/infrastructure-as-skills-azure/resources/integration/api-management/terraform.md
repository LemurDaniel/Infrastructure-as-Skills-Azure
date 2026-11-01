# Rendering API Management as Terraform

Mapping from the question set to the instance. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-apimanagement-service/azurerm` | **v0.1.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.1.0`; the module is
at its first minor, so expect inputs to move.

**AzAPI-based with an `azurerm` constraint**: it takes `resource_group_name` (a name) and
requires `azapi ~> 2.4` and `azurerm >= 4.0, < 5.0` - **a root calling it cannot be on 5.x** - plus
`modtm`, `random >= 3.5, < 4.0`, and Terraform `>= 1.9`. The root's provider set is the union
with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "api_management" {
  source  = "Azure/avm-res-apimanagement-service/azurerm"
  version = "~> 0.1.0"

  name                = data.naming_name.api_management.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: api-management.service.publisher_name, publisher_email - the module default is a placeholder
  publisher_name  = var.publisher_name
  publisher_email = var.publisher_email

  # decision: api-management.service.sku, capacity - the module default is Developer_1
  sku_name = "StandardV2_1"
  zones    = null

  managed_identities = {
    system_assigned = true
  }

  # decision: api-management.networking.network_integration
  virtual_network_type      = "Internal"
  virtual_network_subnet_id = var.apim_subnet_id
  # decision: api-management.networking.public_network_access - a bool, module default true
  public_network_access_enabled = false

  # decision: api-management.security.legacy_protocols_disabled
  security = {
    enable_frontend_ssl30 = false
    enable_frontend_tls10 = false
    enable_frontend_tls11 = false
    enable_backend_ssl30  = false
    enable_backend_tls10  = false
    enable_backend_tls11  = false
  }
  client_certificate_enabled = false

  # decision: api-management.access.caller_authentication, rate_limit_calls_per_minute
  policy = {
    xml_content = local.apim_global_policy
  }

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
      log_categories        = ["GatewayLogs"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.api_management.resource_id }
```

### The global policy

`caller_authentication` and `rate_limit_calls_per_minute` render into the service-level policy, so
they are one `local` and one test. For `entra_id`:

```hcl
locals {
  apim_global_policy = <<-XML
    <policies>
      <inbound>
        <base />
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401">
          <openid-config url="https://login.microsoftonline.com/${data.azurerm_client_config.this.tenant_id}/v2.0/.well-known/openid-configuration" />
          <audiences><audience>${var.api_audience}</audience></audiences>
        </validate-jwt>
        <rate-limit-by-key calls="600" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
      </inbound>
      <backend><base /></backend>
      <outbound><base /></outbound>
      <on-error><base /></on-error>
    </policies>
  XML
}
```

`var.api_audience` is the app registration the callers request tokens for - an `open:` entry owned
by the identity team, since app registrations are not rendered. The counter key is the caller's
address here; per-identity limiting uses the token's `oid` claim.

### Tests

`mock_provider "azapi"` and `"azurerm"` (and `modtm`) keep the plan credential-free; the instance
is an `azapi_resource`, so asserts target its `body.sku`, `body.properties.virtualNetworkType`,
`publicNetworkAccess`, `customProperties` and the policy resource's `body.properties.value`
(`validate-jwt`, `rate-limit-by-key calls="600"`) - exact paths are read off a first
`terraform test` on the pinned version. Private endpoint, role assignments, diagnostic setting and
the portal are marked `# not-testable:` with a reason.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
