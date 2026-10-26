# Rendering a policy assignment as Terraform

Mapping from the question set to the assignments, their definitions and exemptions. General
layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/terraform-idiom.md).
Nothing here renders when `policy_ownership` is `platform`.

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-ptn-policyassignment/azurerm` | **v0.2.2** | 2026-10-26 | Available (pattern) |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../plugins/infrastructure-as-skills-azure/core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`. There is no
resource module for `Microsoft.Authorization/policyAssignments` in the Terraform index; the
pattern module is one assignment with its role assignments and exemptions, so one call per entry
of `assignments` and per baseline control. A custom definition or initiative has no module in
either target and is authored beside the call.

**AzAPI-based with an `azurerm` constraint**: it writes the assignment and the exemptions through
`azapi_resource` and the role assignments through `azurerm_role_assignment`, and requires
`azurerm ~> 4.0` - **a root calling it cannot be on 5.x** - plus `azapi ~> 2.12`, `time ~> 0.9`
and Terraform `~> 1.6`. No `modtm`, no `random`. The scope is an id (`/subscriptions/<id>`,
`/providers/Microsoft.Management/managementGroups/<id>`, a resource group id), which is how the
one module serves all three scope kinds.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `scope_kind`, `subscription_id`, `management_group` | `scope` | The id of the scope; the stage's subscription, the platform's group or the group's id |
| `definition_source`, `custom_definition_file` | `policy_definition_id` | A built-in GUID under `/providers/Microsoft.Authorization/policyDefinitions/`, or the id output of the authored definition / initiative below |
| `definition_version` | *none* | Not carried by the module; the assignment follows the newest version. Named in the handover |
| `assignments[].key`, display name | `name`, `display_name`, `description` | `name` is the resource name (24 / 64 characters); `display_name` is what the portal shows |
| `assignments[].parameters`, `allowed_locations`, `required_tags` | `parameters = { <name> = { value = ... } }` | ARM shape; `null` for a definition without parameters |
| `enforcement_mode` | `enforce` | The enum, `"Default"` / `"DoNotEnforce"` |
| `not_scopes` | `not_scopes` | |
| `non_compliance_message` | `non_compliance_messages = [{ message }]` | A `policy_definition_reference_id` per member for an initiative |
| `resource_selectors` | `resource_selectors` | |
| `overrides` | `overrides` | |
| `exemptions`, `exemption_expiry_required` | `exemptions = [{ resource_id, exemption_category, policy_definition_reference_ids }]` | The module's exemption object carries **no `expires_on`, `display_name` or `description`** in v0.2.2 - an exemption with an expiry is authored (`azurerm_*_policy_exemption`) beside the call |
| `location` | `location` | Required by the module even without an identity |
| `identity`, `user_assigned_identity` | `identity = { type, userAssignedIdentities = { <id> = {} } }` | `null` for `none`; the map key is the identity's resource id |
| `identity_role_definitions` | `role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | The identity's `principal_id` is the user-assigned identity module's output; the module waits before assigning |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `policy_ownership`, `baseline_assignments`, `allowed_locations_scope` | *the calls that exist* | Each listed baseline control is one call with the built-in's GUID; the region list is computed from `location` and the residency answer |

### The call

```hcl
module "policy_allowed_locations" {
  source  = "Azure/avm-ptn-policyassignment/azurerm"
  version = "~> 0.2.0"

  # decision: policy.placement.scope_kind / subscription_id
  scope = "/subscriptions/${var.subscription_id}"
  # decision: policy.definition.definition_source - builtin
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
  name                 = "pol-allowed-locations"
  display_name         = "Allowed locations"
  description          = "Resources may only be created in the regions of the data residency decision"
  # decision: policy.assignments.enforcement_mode
  enforce = "Default"
  # decision: policy.assignments.allowed_locations_scope / allowed_locations - computed from location, global added
  parameters = {
    listOfAllowedLocations = { value = ["germanywestcentral", "germanynorth", "global"] }
  }
  # decision: policy.assignments.not_scopes
  not_scopes = []
  # decision: policy.assignments.non_compliance_message
  non_compliance_messages = [{ message = "Only the regions of the data residency decision are allowed." }]
  # decision: policy.assignments.resource_selectors / overrides
  resource_selectors = []
  overrides          = []
  # decision: policy.identity.identity - none for a Deny policy
  identity = null
  location = var.location
  # decision: policy.assignments.exemptions - without expiry here; with one, authored below
  exemptions = []
  metadata   = { assignedBy = "terraform" }
  # decision: deployment.module_telemetry
  enable_telemetry = false
}

module "policy_deploy_diagnostics" {
  source  = "Azure/avm-ptn-policyassignment/azurerm"
  version = "~> 0.2.0"

  scope                = "/subscriptions/${var.subscription_id}"
  policy_definition_id = azurerm_management_group_policy_set_definition.custom.id
  name                 = "pol-deploy-diag"
  display_name         = "Deploy diagnostic settings"
  enforce              = "Default"
  parameters           = null
  not_scopes           = []
  non_compliance_messages = []
  # decision: policy.identity.identity - user_assigned; location is required with an identity
  identity = {
    type                   = "UserAssigned"
    userAssignedIdentities = { (module.policy_identity.resource_id) = {} }
  }
  location = var.location
  # decision: policy.identity.identity_role_definitions - the roles the definition names, on the scope
  role_assignments = {
    contributor = {
      role_definition_id_or_name = "Contributor"
      principal_id               = module.policy_identity.principal_id
      principal_type             = "ServicePrincipal"
    }
  }
  exemptions       = []
  enable_telemetry = false
}

output "policy_allowed_locations_id" { value = module.policy_allowed_locations.resource_id }
```

Outputs are `resource_id`, `policy_assignment_id`, `policy_assignment_name` and
`role_assignments`; `resource` is deprecated. One call per assignment: the module has no list
input, and a key per call (`policy_<key>`) is the stable address.

### Tests

`mock_provider "azurerm"`, `mock_provider "azapi"` and `mock_provider "time"` keep the plan
credential-free. The assignment is an `azapi_resource` inside the module, so its body is known at
plan time: asserts address `module.policy_<key>.azapi_resource.policy_assignment` and read
`body.properties.policyDefinitionId`, `enforcementMode`, `parameters`, `notScopes`,
`nonComplianceMessages`, `resourceSelectors`, `overrides`, `identity.type` and `location`
(the exact address is read off a first `terraform test` run on the pinned version, not recalled).
The role assignments are `# not-testable:` where the principal id is unknown at plan time;
`definition_version` is `# not-testable:` because the module does not carry it;
`exemption_expiry_required` and `policy_ownership` are checks on the spec, not attributes of the
plan.

## Authored rendering

The fallback - `implementation: authored`, a root on `azurerm` **5.x**, or a repository that already
renders assignments this way. Checked against `terraform providers schema -json` (5.11.0). The
custom definition and initiative are always authored; the exemption with an expiry too.

| Decision | Resource and argument |
|---|---|
| `scope_kind: subscription` | `azurerm_subscription_policy_assignment`, `subscription_id = "/subscriptions/<id>"` |
| `scope_kind: management_group` | `azurerm_management_group_policy_assignment`, `management_group_id` |
| `scope_kind: resource_group` | `azurerm_resource_group_policy_assignment`, `resource_group_id` |
| `definition_source: custom_definition` | `azurerm_policy_definition` (`policy_type = "Custom"`, `mode`, `policy_rule = file(...)`, `parameters = file(...)`, `management_group_id` to create it at the group) |
| `definition_source: custom_initiative` | `azurerm_management_group_policy_set_definition` at a group (the subscription-scoped `azurerm_policy_set_definition` has no group argument in 5.x), `policy_definition_reference { policy_definition_id, reference_id }` |
| `definition_version` | *not carried* - named in the handover |
| display name, description | `display_name`, `description`, `metadata = jsonencode(...)` |
| `parameters`, `allowed_locations`, `required_tags` | `parameters = jsonencode({ <name> = { value = ... } })` - a JSON string here, an object in the module |
| `enforcement_mode` | `enforce` - a **bool**: `Default` → `true`, `DoNotEnforce` → `false` |
| `not_scopes` | `not_scopes` |
| `non_compliance_message` | `non_compliance_message { content, policy_definition_reference_id }` |
| `resource_selectors` | `resource_selectors { name, selectors { kind, in, not_in } }` |
| `overrides` | `overrides { value, selectors { in, not_in } }` |
| `identity`, `user_assigned_identity`, `location` | `identity { type = "UserAssigned", identity_ids = [...] }` with `location` |
| `identity_role_definitions` | `azurerm_role_assignment` on the scope, `principal_id` the identity's, a `time_sleep` between identity and assignment |
| `exemptions`, `exemption_expiry_required` | `azurerm_subscription_policy_exemption` / `azurerm_resource_group_policy_exemption` / `azurerm_resource_policy_exemption` / `azurerm_management_group_policy_exemption`: `policy_assignment_id`, `exemption_category`, `expires_on`, `display_name`, `policy_definition_reference_ids` |

```hcl
# decision: policy.definition.definition_source - custom_definition, created at the group so it can be assigned anywhere below
resource "azurerm_policy_definition" "custom" {
  name                = "deny-storage-without-tls12"
  policy_type         = "Custom"
  mode                = "Indexed"
  display_name        = "Storage accounts must use TLS 1.2"
  management_group_id = var.management_group_id
  policy_rule         = file("${path.module}/policies/deny-storage-without-tls12.rule.json")
  parameters          = file("${path.module}/policies/deny-storage-without-tls12.parameters.json")
  metadata            = jsonencode({ category = "Storage" })
}

# decision: policy.placement.scope_kind - subscription
resource "azurerm_subscription_policy_assignment" "allowed_locations" {
  name                 = "pol-allowed-locations"
  subscription_id      = "/subscriptions/${var.subscription_id}"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
  display_name         = "Allowed locations"
  # decision: policy.assignments.enforcement_mode - a bool here
  enforce = true
  # decision: policy.assignments.allowed_locations_scope - computed, global added
  parameters = jsonencode({ listOfAllowedLocations = { value = ["germanywestcentral", "germanynorth", "global"] } })
  # decision: policy.assignments.not_scopes
  not_scopes = []
  # decision: policy.assignments.non_compliance_message
  non_compliance_message {
    content = "Only the regions of the data residency decision are allowed."
  }
}

# decision: policy.placement.scope_kind - management_group, with an identity for deployIfNotExists
resource "azurerm_management_group_policy_assignment" "deploy_diagnostics" {
  name                 = "pol-deploy-diag"
  management_group_id  = var.management_group_id
  policy_definition_id = azurerm_management_group_policy_set_definition.custom.id
  display_name         = "Deploy diagnostic settings"
  enforce              = true
  # decision: policy.identity.identity - user_assigned; location is required with an identity
  location = var.location
  identity {
    type         = "UserAssigned"
    identity_ids = [module.policy_identity.resource_id]
  }
}

# decision: policy.identity.identity_role_definitions - wiring on the scope
resource "azurerm_role_assignment" "deploy_diagnostics" {
  scope                = var.management_group_id
  role_definition_name = "Contributor"
  principal_id         = module.policy_identity.principal_id
  principal_type       = "ServicePrincipal"
}

# decision: policy.assignments.exemptions - with the expiry exemption_expiry_required demands
resource "azurerm_resource_group_policy_exemption" "sandbox" {
  name                 = "sandbox-waiver"
  resource_group_id    = var.sandbox_resource_group_id
  policy_assignment_id = azurerm_subscription_policy_assignment.allowed_locations.id
  exemption_category   = "Waiver"
  expires_on           = "2027-01-01T00:00:00Z"
  display_name         = "Sandbox may use other regions until the migration"
}
```

Every decision is observable in the plan of the authored resources (`enforce`, `parameters` as a
JSON string compared with `jsonencode`, the blocks, `identity[0].type`, `location`,
`expires_on`), so the authored tests carry one assert per decision and no marker but
`definition_version` and the two spec-only checks.
