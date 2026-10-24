# Resource groups: roles, modes, rendering

The deployment set decides [which areas get a group of their own and whether each group is
created](../../iac-authoring/questions/deployment.yaml) (`resource_group_split`,
`resource_group_mode_<role>`, `resource_group_lock`). This file is what the renderer does
with the answers.

## Roles

`main` is `context.resource_group_name` and always exists. The other roles exist only when
`resource_group_split` lists them. A resource belongs to the group of its role; a role that is
not split off is part of `main`.

The table below is the prose of [resource-group-roles.yaml](resource-group-roles.yaml), which the
diagram and the decision document read; change both together.

| Role | Resources (default) |
|---|---|
| `network` | virtual network, subnets, network security group, route table, private DNS zone |
| `data` | storage account, Cosmos DB |
| `application` | App Service plan and app, function app, Container Apps, container registry, AI Foundry, AI Search |
| `observability` | Log Analytics workspace, Application Insights |
| `security` | Key Vault, user-assigned identity |

- A **private endpoint** lives in the group of the resource it serves, not in `network`: it is
  that resource's front door, and the consumer's RBAC reaches it that way. Its subnet is
  referenced across groups.
- A resource may depart from the table; the spec records it as `placement.resource_group: <role>`
  on the resource, `source: overridden`, with the reason in a comment. Without the key the table
  applies.
- Where a role's group is in mode `existing`, the resources in it still render — the group is
  only read.

## Modes

| Mode | Terraform | Bicep |
|---|---|---|
| `existing` | `variable resource_group_name[_<role>]` per stage file; a `data "azurerm_resource_group"` where a module needs the id (`parent_id`) | `param resourceGroupName[<Role>]` per stage file; `existing` resource for the scope |
| `create` | the AVM resource group module (`avm-res-resources-resourcegroup`); name from the naming interface, or a stated `context.resource_group_name[_<role>]` verbatim as a stage parameter | the AVM resource group module (`avm/res/resources/resource-group`), deployed at **subscription scope** |

Versions are looked up live ([avm.md](avm.md)); the table there is a dated snapshot.

- **Name of a created group:** `Azure::Microsoft.Resources/resourceGroups`, abbreviation `rg`,
  the workload plus the role as name — `rg-we-prod-payments-01` for `main`,
  `rg-we-prod-payments-data-01` for `data`. Check the result against `naming.yaml` before
  relying on the segment form.
- **Location** comes from `context.location`; a created group has one, an existing group's
  location is not read.
- **Tags** are `context.tags`, like every other resource.
- **Lock:** `resource_group_lock` — `CanNotDelete` on each created group in `production` (default),
  in every stage, or none. A group in mode `existing` never gets a lock from this render.
- **Order:** every resource in a created group depends on the group through its id or name
  output; never a module-level `depends_on` ([terraform-idiom.md](terraform-idiom.md)).

## What `create` changes elsewhere

- **Bicep scope.** One `create` anywhere makes the root `targetScope = 'subscription'`; each
  resource module takes `scope: resourceGroup(<name>)`. All-`existing` stays at resource-group
  scope with one `scope:` per module for the roles that differ.
- **Pipeline.** A subscription-scope root deploys with `az deployment sub` instead of
  `az deployment group`, and the stage identity needs Contributor on the subscription (stage
  isolation `subscription`) — not on the group. The pipeline reference lists the role; see
  [pipelines.md](pipelines.md).
- **Terraform state.** A created group is in the state of the stage; the pipeline's `destroy`
  (if any) removes it. The lock stops that in production, deliberately.
- **Tests.** One `assert` per group decision: `# decision: deployment.resource_group_mode_<role>`
  checks the group resource planned (create) or absent (existing); `resource_group_lock` checks
  the lock in the stages it names, `# not-testable:` where a plan cannot observe it.
  `# decision: <resource>.placement.resource_group` checks the resource's group.

## Not decided here

A subscription is never created. A group the platform hands out is never given a lock, a
role assignment or a policy by this render — those are the platform's, and a render that
sets them fights the platform's own assignment.
