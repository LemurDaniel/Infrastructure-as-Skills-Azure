# Management group - what the question set cannot express

## It is the platform's backbone

Policy and RBAC inherit along the management group hierarchy, and the Azure landing zone pattern
(`avm-ptn-alz` in Terraform, `avm/ptn/alz/empty` in Bicep) builds and reconciles that hierarchy -
*platform*, *landing zones*, *corp*, *online*, *sandbox*, *decommissioned* - with every ALZ policy
and role assignment on it. This set is deliberately smaller: **one group hung under an existing
one**, for a team or a workload that needs a scope of its own below *landing zones*, and for a
tenant without a hierarchy (`landing_zone: standalone`). `management_group_ownership: platform`
(the default) renders nothing; a group the workload needs is an `open:` entry for the platform
team. A workload that renders the hierarchy itself is a second writer to the platform's own
pattern.

## Fixed at creation

- **The id.** It is the resource name, tenant-unique and immutable; a different id is a new
  group, and every policy assignment and role assignment scope below carries it. Up to 90
  characters of letters, digits, `-`, `_`, `.`, `(`, `)`; no leading or trailing period.
- **Nothing else.** The display name changes in place; the parent changes by a move, which is an
  update of the group and re-evaluates inherited policy on every subscription below - a move is a
  change window, not a rename.

## Ordering

The parent exists first (the platform's). Then the group, then the subscriptions moved in, then the
role assignments at the group, then anything that references the group's id - policy assignments
(`policy` set) and vended subscriptions (`subscription` set, `management_group`). Inherited policy
takes effect on a moved subscription from its next evaluation, usually within half an hour; a
`Deny` inherited from the new parent stops that subscription's next non-compliant deployment.

A newly created group is visible to the deploying identity only after the tenant's RBAC caches
catch up - a minute or two. A root that creates the group and assigns a policy at it in the same
run can fail on the first apply with an authorisation error at the new scope and succeed on the
second; the Bicep render separates the two deployments, the Terraform render puts a `time_sleep`
between the group and its first dependent.

## Pitfalls

**Tenant-level rights.** Creating a group needs `Management Group Contributor` on the parent, and
the Bicep resource module's own notes name a tenant-level deployment: without `Owner` at `/`, the
pair `Automation Job Operator` at `/` plus `Management Group Contributor` at the top group suffices
for a pipeline identity. Moving a subscription needs rights on both ends. The handover lists them.

**The two Bicep modules deploy at different scopes.** The resource module
(`avm/res/management/management-group`) is deployed at **management group** scope (the parent); the
placement pattern (`avm/ptn/mgmt-groups/subscription-placement`) at **tenant** scope, which from the
parent's deployment is `scope: tenant()`. Mixing them up fails at `bicep build`, not at deploy time.

**No Terraform module.** `avm-res-management-managementgroup` is `Proposed` in the index; the render
is authored `azurerm_management_group`, which also carries `subscription_ids` - a second way to move
subscriptions beside `azurerm_management_group_subscription_association`. The render uses the
association resource and never both: `subscription_ids` on the group makes the group the owner of
the whole membership and removes any subscription the list does not name.

**A subscription has one parent.** Listing it here and vending it into a group elsewhere
(`subscription` set) is two writers; the association is written once, in the set that creates the
subscription when it does, here otherwise.

**The default management group for new subscriptions** is a hierarchy setting of the tenant root,
not of this group; a new subscription created outside a vending flow lands there, not here.

**Deleting a group** fails while it has children: subscriptions and child groups are moved out
first, and the policy and role assignments at the group disappear with it.

## Not covered here, and why

The ALZ hierarchy and its policy set (`avm-ptn-alz`, `avm/ptn/alz/empty`), hierarchy settings
(default group, authorisation requirement), the group's activity-log diagnostic setting, custom role
definitions scoped to a group, and Azure Lighthouse delegations each carry decisions of their own
and have no question set; a request for one is said out loud, not improvised.
