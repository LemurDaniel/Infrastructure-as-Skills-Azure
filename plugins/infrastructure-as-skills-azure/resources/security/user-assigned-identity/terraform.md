# Rendering a user-assigned identity as Terraform

Mapping from the question set to the identity. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-managedidentity-userassignedidentity/azurerm` | **v0.5.3** | 2026-10-23 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.5.0`.

**`azurerm`-based**: it takes `resource_group_name` and requires `azurerm >= 4.60.0, < 5.0.0`
- a root calling it cannot be on 5.x - plus `azapi ~> 2.12`, `modtm ~> 0.3`, `random ~> 3.5`,
Terraform `>= 1.9`. The root's provider set is the union with the other modules.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Decision | Input | Note |
|---|---|---|
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "identity" {
  source  = "Azure/avm-res-managedidentity-userassignedidentity/azurerm"
  version = "~> 0.5.0"

  name                = data.naming_name.identity.name
  location            = var.location
  resource_group_name = var.resource_group_name

  # decision: user-assigned-identity.identity.federated_credentials
  federated_identity_credentials = {
    pipeline = {
      name     = "github-production"
      issuer   = "https://token.actions.githubusercontent.com"
      subject  = "repo:org/repo:environment:production"
      audience = ["api://AzureADTokenExchange"]
    }
  }
  # decision: user-assigned-identity.identity.isolation_scope - None is unset
  isolation_scope = null

  enable_telemetry = true
  tags             = merge(local.tags, { purpose = var.purpose })
}

output "id" { value = module.identity.resource_id }
output "principal_id" { value = module.identity.principal_id }
output "client_id" { value = module.identity.client_id }
```

The outputs are what the consumers and the roles take: `principal_id` for a role assignment,
`resource_id` for the consumer's `user_assigned_identity_ids`. Output names are read from the
README of the pinned version.

### Tests

With `azurerm` mocked, asserts target the plan of the module's resources: the name, the tags,
the federated credentials' issuer and subject, the isolation scope. Role assignments built in
the module are `# not-testable:` where the plan hides them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

| Decision | Resource |
|---|---|
| the identity | `azurerm_user_assigned_identity` |
