# Role assignments

A role is a relationship between two parts of a system, so the spec records it once, in
`wiring.role_assignments`, and no resource set asks for it
([spec.md](../../iac-authoring/references/spec.md#patterns-and-the-wiring)). This is the one
place that says how an entry renders; a resource's `terraform.md` and `bicep.md` add only what
is particular to that resource.

```yaml
wiring:
  role_assignments:
    value:
    - from: app-service__chat              # a resource of the spec: its identity holds the role
      to: storage-account                  # the resource the role is on - the scope
      role: Storage Blob Data Reader       # a name of built-in-roles.yaml
    - from: { existing: entra_group }      # a principal outside the spec, its id per stage
      to: key-vault
      role: Key Vault Secrets Officer
    source: stated
```

One list holds for every stage. The render digest prints each entry with what the render needs:
the target's key and its AVM module, the role and its model, where the principal id comes from.

## Where it renders

**In the root, never in a module the render writes** - `main.bicep`, or the root's `.tf` files.
Only the root sees both ends: the target's id and the principal's id are outputs of two
different modules, and a module that took the other's principal as an input would know about
a consumer it has no business knowing. In a composition of family modules the family exposes
the id and the principal id as outputs, and the assignment stands in the root between them.

## How an entry renders

| The target (`to`) is... | Rendered as |
|---|---|
| An AVM module call in the root whose module has the role interface | **An entry of that call's interface**, written in the root: `role_assignments = { <key> = { role_definition_id_or_name, principal_id, principal_type } }` in Terraform, `roleAssignments: [ { roleDefinitionIdOrName, principalId, principalType } ]` in Bicep ([avm.md](avm.md#the-shared-interfaces)). The role by name; the assignment is created and destroyed with the target |
| The same, but the principal's module already reads an output of the target (the app takes the vault's URI, the endpoint of the account) | **A standalone assignment in the root.** Through the interface the two modules would need each other: a cycle in Bicep, where a module is one deployment, and a target that waits for its own consumer anywhere |
| Authored, called inside a family module, or its module has no role input (below) | **A standalone assignment in the root**, scoped to the target's id |

A standalone assignment is, per target:

- **Terraform**: one `azurerm_role_assignment` per entry (`for_each` over a local map keyed
  `<to>/<from>/<role>`): `scope` the target's id output, `role_definition_name` the role,
  `principal_id`, `principal_type`. A root that calls the role assignment utility module puts
  the entries into that one call instead
  ([role-assignment/terraform.md](../../../resources/security/role-assignment/terraform.md)).
- **Bicep**: one `Microsoft.Authorization/roleAssignments` per entry with `scope:` an
  `existing` symbol of the target - never the id string -, `name: guid(<scope id>, <principal>,
  <role>)` so the same spec always names the same assignment, `principalId`, `principalType` and
  `roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '<guid>')`.
  The GUID is the role's id in
  [built-in-roles.yaml](../../iac-authoring/references/built-in-roles.yaml), never recalled.

A map key on the Terraform side is the entry's own (`<from>_<role>`), never an index: it is the
assignment's address, and an index moves when the list does.

## Where the principal id comes from

| `from` | Principal id | `principal_type` |
|---|---|---|
| A `user-assigned-identity` resource of the spec | The identity module's `principal_id` / `principalId` output | `ServicePrincipal` |
| Any other resource of the spec - its system-assigned identity | The resource module's principal id output (read its name from the README of the pinned version); `identity[0].principal_id` of an authored resource | `ServicePrincipal` |
| `{ existing: principal }` - a workload identity outside the spec (a service principal, an identity another deployment owns) | An id parameter (`variable` / `param`) filled from each stage file, as for every `{ existing }` reference; the all-zero GUID while an `open:` entry names `wiring.role_assignments` | `ServicePrincipal` |
| `{ existing: entra_group }` - people | The same: the group's object id per stage from the stage file | `Group` |

The type is always written. With it Azure does not look the principal up in the directory
before writing the assignment, and an identity created seconds earlier - not yet replicated -
is not refused as `PrincipalNotFound`. A managed identity is a `ServicePrincipal`; the API has
no value of its own for it. People get a role through a group, never as a person: the access
outlives them.

A resource that acts with a user-assigned identity holds no role itself - the entry names the
identity as `from`. A principal id is never a literal in the template and never looked up with
a data source: `plan` would need read access to the directory.

## The scope

`to` is always a resource of the spec, and its id is the scope. A narrower scope is a narrower
resource: a `blob-container`, `file-share` or `queue` instead of the account, a
`key-vault-secret` or `key-vault-key` instead of the vault (the versionless id). A scope that
is no resource of the spec - a resource group, a subscription, a platform resource - is not
wiring: it is a `role-assignment` resource with its own set
([notes](../../../resources/security/role-assignment/notes.md)).

## Cosmos DB's data roles

`Cosmos DB Built-in Data Reader` and `Cosmos DB Built-in Data Contributor` are roles of Cosmos
DB's own model (`data_plane` in built-in-roles.yaml), assigned through the account and not
through `Microsoft.Authorization`. The entry looks like any other; the role's name tells the
render which model it is:

- **Terraform**: the module has no input for them - one `azurerm_cosmosdb_sql_role_assignment`
  per entry beside the call, `role_definition_id = "<account id>/sqlRoleDefinitions/<guid>"`
  (`...0001` reader, `...0002` contributor), `scope` the account id.
- **Bicep**: `sqlRoleAssignments: [ { principalId, roleDefinitionId, scope } ]` on the module,
  `roleDefinitionId` the full id of the built-in definition; authored, a child
  `sqlRoleAssignments` resource of the account.

An Azure role on the same account (`Contributor`, a reader) is the control plane and renders
as every other entry does.

## Where a module departs from the interface

| Target | Terraform | Bicep |
|---|---|---|
| `blob-container`, `queue`, `file-share` | On the storage module: `containers.<key>.role_assignments`, `queues.<key>.role_assignments`, `shares.<key>.role_assignments`. Authored, a share's scope is `rbac_scope_id`, not its resource id | `blobServices.containers[].roleAssignments`, `queueServices.queues[].roleAssignments`, `fileServices.shares[].roleAssignments`; authored, an extension resource scoped to the child |
| `key-vault-secret`, `key-vault-key` | The key or secret module's `role_assignments`, scoped to the versionless id | The same; the key module knows a fixed set of role names - read its README |
| `cosmos-db` | Azure roles: `role_assignments` without `principal_type`. Data roles: above | Data roles: above |
| `public-dns-zone` | No role input: standalone, scope the zone's id | `roleAssignments` |
| `container-instances` | `role_assignments` | No role parameter: standalone, scoped to the group, by role definition id |
| `bot-service` | `role_assignments` | No AVM module: authored, by role definition id |
| `communication-services` | On the e-mail module only; the communication resource takes a standalone assignment | `roleAssignments` on both modules |
| `relay-namespace` | A role on one hybrid connection is standalone, on the submodule's `resource_id` | `hybridConnections[].roleAssignments` |
| `network-watcher` | `role_assignments` | `roleAssignments` on the watcher module; the flow-log module has none - under `platform` a standalone assignment on the watcher in `NetworkWatcherRG` |
| `event-grid-system-topic` | | `externalResourceRoleAssignments` exists and is not used: a role on a delivery target is an entry with that target as `to` |

A row here is a dated reading of the module; re-read the README of the version pinned.

## Order and propagation

The target and the principal first, then the assignment, then whatever relies on the access -
the consumer starts last. A new assignment takes minutes to become effective: where a
data-plane write follows in the same deployment (a secret, a blob), the write waits for the
assignment (a `time_sleep` after it in Terraform, `dependsOn` on the assignment in Bicep),
never a retry loop.

Writing an assignment needs `Role Based Access Control Administrator` on the scope, which
`Contributor` does not include; `deployment.deployer_roles` derives it
([spec.md](../../iac-authoring/references/spec.md#delivery-the-pipeline)).

## Tests

The decision is `wiring.role_assignments`, and it is the one decision key several tests may
carry - one per target the entries land on:

```hcl
# decision: wiring.role_assignments
assert {
  condition     = azurerm_role_assignment.this["storage-account/app-service/Storage Blob Data Reader"].role_definition_name == "Storage Blob Data Reader"
  error_message = "The app reads blobs, and nothing else is granted on the account."
}
```

In Bicep it is a `decision: wiring.role_assignments` entry of the `.armtest.yaml` against the
compiled assignment. An entry set through a module's interface lands in a child the plan does
not expose and is marked `# not-testable: wiring.role_assignments - set through the module's
role_assignments input; the module's own tests cover the mapping`.
`check_render_coverage.py` holds a spec with role assignments to at least one such marker.
