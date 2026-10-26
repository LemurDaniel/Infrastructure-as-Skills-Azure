# Rendering a policy assignment as Bicep

Mapping from the question set to the assignments, their definitions and exemptions. General
layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).
Nothing here renders when `policy_ownership` is `platform`.

```bash
bicep build --stdout main.policy.bicep
```

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `br/public:avm/ptn/authorization/policy-assignment:<version>` | **0.5.3** | 2026-10-26 | Available (pattern) |
| `br/public:avm/ptn/authorization/policy-exemption:<version>` | **0.2.0** | 2026-10-26 | Available (pattern) |

The index also lists a resource module `avm/res/authorization/policy-assignment` with a child per
scope (`mg-scope`, `sub-scope`, `rg-scope`) as Available, but the registry holds **no published
tag** for it (checked 2026-10-26); the pattern module is the one that exists, and the table is
re-checked before a render. There is no module for a policy definition or initiative in either
target; both are authored beside the call. Pin the exact version.

**The pattern module's `targetScope` is `managementGroup`.** It takes the actual scope as a
parameter - `managementGroupId` (default: the deployment's group), `subscriptionId`, or
`subscriptionId` + `resourceGroupName` - and deploys the assignment there with a nested deployment.
So a policy root is deployed at management group scope (`az deployment mg create`) even for a
subscription-scoped assignment, and the deploying identity needs `Resource Policy Contributor`
at that group or the subscription. A repository that deploys at subscription scope only uses the
authored resource below.

**Always write `identity`.** The module defaults it to `SystemAssigned`; a `Deny` gets an unused
identity and a location dependency. `'None'` on every call without `deployIfNotExists` / `modify`.

### Decision -> module parameter

| Decision | Parameter | Note |
|---|---|---|
| `scope_kind`, `subscription_id`, `management_group` | `managementGroupId` / `subscriptionId` / `subscriptionId` + `resourceGroupName` | The subscription id is a GUID here, not `/subscriptions/...` |
| `definition_source`, `custom_definition_file` | `policyDefinitionId` | A built-in id, or the authored definition's / initiative's `.id` |
| `definition_version` | `definitionVersion` | `'1.*'`; omitted when empty (newest) |
| `assignments[].key`, display name | `name`, `displayName`, `description` | 24 / 64 characters for `name` |
| `assignments[].parameters`, `allowed_locations`, `required_tags` | `parameters: { <name>: { value: ... } }` | `parameterOverrides` is for a loaded JSON file; not used |
| `enforcement_mode` | `enforcementMode` | `'Default'` / `'DoNotEnforce'` |
| `not_scopes` | `notScopes` | |
| `non_compliance_message` | `nonComplianceMessages: [ { message } ]` | |
| `resource_selectors` | `resourceSelectors` | |
| `overrides` | `overrides` | |
| `identity`, `user_assigned_identity` | `identity: 'None' / 'SystemAssigned' / 'UserAssigned'`, `userAssignedIdentityId` | |
| `location` | `location` | Module default `deployment().location`; written |
| `identity_role_definitions` | `roleDefinitionIds: [ '/providers/Microsoft.Authorization/roleDefinitions/<guid>' ]` | **Ids, not names** - resolved through a table checked against the live definitions; `additional*IDsToAssignRbacTo` for further scopes, not used |
| `exemptions`, `exemption_expiry_required` | the exemption module: `policyAssignmentId`, `exemptionCategory`, `expiresOn`, `displayName`, `policyDefinitionReferenceIds`, scope parameters | One module call per entry |
| `deployment.module_telemetry` | `enableTelemetry` | |
| `policy_ownership`, `baseline_assignments`, `allowed_locations_scope` | *the calls that exist* | One call per baseline control with the built-in's id |

### The call

```bicep
targetScope = 'managementGroup'

param location string
param subscriptionId string
param policyIdentityResourceId string
param enableTelemetry bool = false

// decision: policy.definition.definition_source - custom_definition, authored: no module exists
resource customDefinition 'Microsoft.Authorization/policyDefinitions@2025-01-01' = {
  name: 'deny-storage-without-tls12'
  properties: {
    policyType: 'Custom'
    mode: 'Indexed'
    displayName: 'Storage accounts must use TLS 1.2'
    metadata: { category: 'Storage' }
    parameters: loadJsonContent('policies/deny-storage-without-tls12.parameters.json')
    policyRule: loadJsonContent('policies/deny-storage-without-tls12.rule.json')
  }
}

// decision: policy.definition.definition_source - custom_initiative
resource customInitiative 'Microsoft.Authorization/policySetDefinitions@2025-01-01' = {
  name: 'workload-baseline'
  properties: {
    policyType: 'Custom'
    displayName: 'Workload baseline'
    policyDefinitions: [
      { policyDefinitionId: customDefinition.id, policyDefinitionReferenceId: 'storageTls' }
    ]
  }
}

module policyAllowedLocations 'br/public:avm/ptn/authorization/policy-assignment:0.5.3' = {
  name: 'policy-allowed-locations'
  params: {
    name: 'pol-allowed-locations'
    displayName: 'Allowed locations'
    description: 'Resources may only be created in the regions of the data residency decision'
    // decision: policy.definition.definition_source - builtin
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c'
    // decision: policy.placement.scope_kind - subscription
    subscriptionId: subscriptionId
    // decision: policy.assignments.enforcement_mode
    enforcementMode: 'Default'
    // decision: policy.assignments.allowed_locations_scope - computed from location, global added
    parameters: {
      listOfAllowedLocations: { value: [ 'germanywestcentral', 'germanynorth', 'global' ] }
    }
    // decision: policy.assignments.not_scopes
    notScopes: []
    // decision: policy.assignments.non_compliance_message
    nonComplianceMessages: [ { message: 'Only the regions of the data residency decision are allowed.' } ]
    resourceSelectors: []
    overrides: []
    // decision: policy.identity.identity - none; the module default is SystemAssigned
    identity: 'None'
    location: location
    metadata: { assignedBy: 'bicep' }
    enableTelemetry: enableTelemetry
  }
}

module policyDeployDiagnostics 'br/public:avm/ptn/authorization/policy-assignment:0.5.3' = {
  name: 'policy-deploy-diag'
  params: {
    name: 'pol-deploy-diag'
    displayName: 'Deploy diagnostic settings'
    policyDefinitionId: customInitiative.id
    subscriptionId: subscriptionId
    enforcementMode: 'Default'
    parameters: {}
    // decision: policy.identity.identity - user_assigned
    identity: 'UserAssigned'
    userAssignedIdentityId: policyIdentityResourceId
    location: location
    // decision: policy.identity.identity_role_definitions - ids, resolved from the names
    roleDefinitionIds: [
      '/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor
    ]
    enableTelemetry: enableTelemetry
  }
}

// decision: policy.assignments.exemptions - one call per entry, expiry required
module exemptionSandbox 'br/public:avm/ptn/authorization/policy-exemption:0.2.0' = {
  name: 'policy-exemption-sandbox'
  params: {
    name: 'sandbox-waiver'
    displayName: 'Sandbox may use other regions until the migration'
    policyAssignmentId: policyAllowedLocations.outputs.resourceId
    exemptionCategory: 'Waiver'
    expiresOn: '2027-01-01T00:00:00Z'
    subscriptionId: subscriptionId
    resourceGroupName: 'rg-sandbox'
    location: location
    enableTelemetry: enableTelemetry
  }
}

output policyAllowedLocationsId string = policyAllowedLocations.outputs.resourceId
```

The call was built with `bicep build` against the versions in the table. Outputs of the assignment
module are `name`, `resourceId`, `principalId` and `location`; of the exemption module `name` and
`resourceId`. A management-group-scoped assignment passes `managementGroupId:
managementGroup().name` instead of `subscriptionId`.

### Tests

A module call compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, so every parameter above is observable in `tests/*.armtest.yaml`
([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests)): the definition
id, `enforcementMode`, `parameters`, `identity`, `roleDefinitionIds`, the exemption's `expiresOn`.
The authored definition's `policyRule` is the loaded file's content in the compiled template and
is asserted by its `if.allOf[0].equals`. `policy_ownership` and `exemption_expiry_required` are
`not-testable` as checks on the spec.

## Authored rendering

The fallback, or a repository that deploys at subscription scope and renders assignments as
resources. The scope is the template's `targetScope` (`subscription`, `managementGroup`, or
`resourceGroup`); the resource type is the same at every scope.

```bicep
targetScope = 'subscription'

param location string

resource requireTags 'Microsoft.Authorization/policyAssignments@2025-01-01' = {
  name: 'pol-require-tag-costcenter'
  location: location
  identity: { type: 'None' }
  properties: {
    displayName: 'Require the costCenter tag'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/871b6d14-10aa-478d-b590-94f262ecfa99'
    enforcementMode: 'Default'
    parameters: { tagName: { value: 'costCenter' } }
    notScopes: []
    nonComplianceMessages: [ { message: 'Every resource carries the costCenter tag.' } ]
  }
}
```

| Decision | Property |
|---|---|
| `definition_source` | `properties.policyDefinitionId`; a custom definition is a `Microsoft.Authorization/policyDefinitions@2025-01-01` at the same or a higher scope |
| `definition_version` | `properties.definitionVersion` |
| `enforcement_mode` | `properties.enforcementMode` |
| `parameters`, `allowed_locations`, `required_tags` | `properties.parameters.<name>.value` |
| `not_scopes`, `non_compliance_message`, `resource_selectors`, `overrides` | `properties.notScopes`, `nonComplianceMessages`, `resourceSelectors`, `overrides` |
| `identity`, `user_assigned_identity`, `location` | `identity.type`, `identity.userAssignedIdentities`, `location` |
| `identity_role_definitions` | `Microsoft.Authorization/roleAssignments@2022-04-01` at the scope, `principalId` the identity's (`reference(..., 'Full').identity.principalId` for system-assigned) |
| `exemptions` | `Microsoft.Authorization/policyExemptions@2024-12-01-preview` with `scope:` the exempt resource or group |
