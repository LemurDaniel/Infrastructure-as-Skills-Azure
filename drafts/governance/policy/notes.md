# Azure Policy assignment - what the question set cannot express

## It is a scope setting, and the platform usually owns it

An assignment lives on a management group, a subscription or a resource group and applies to
everything below. In an application landing zone the platform assigns the ALZ baseline at the
management groups - allowed locations, the denies on public network access, the
`deployIfNotExists` policies that write diagnostic settings and private DNS records - and the
workload inherits all of it (guardrails, section 0). `policy_ownership: platform` (the default)
renders **nothing**; a control the workload needs and does not inherit is an `open:` entry for the
platform team. `deployment` (forced for `landing_zone: standalone`) is for a subscription nothing
governs, or for a platform run that builds the governance itself.

Two assignments of the same control at different scopes do not conflict, they **intersect**: the
narrower `Allowed locations` wins, the stricter `Deny` wins, and nobody is told. That is the reason
the default renders nothing and the baseline list is empty until a `standalone` deployment makes it
necessary.

## Fixed at creation

- **The scope.** It is part of the resource id; a different scope is a new assignment and the
  compliance history starts over.
- **The name.** 24 characters at management group scope, 64 below; it is what exemptions and
  remediations reference.
- **The definition.** `policy_definition_id` is immutable on the assignment; a different
  definition is a new assignment. A built-in's *version* can move (`definition_version`), its id
  cannot.
- **A custom definition's scope.** A definition created at a subscription cannot be assigned at a
  management group, and cannot be moved up afterwards; the definition is created at the highest
  scope it will ever be assigned at.
- **The identity type.** Switching between system- and user-assigned recreates the identity and
  its role assignments.

## Ordering

The identity (`user-assigned-identity` set), then its role assignments on the scope, then the
custom definition or initiative, then the assignment, then the exemptions - an exemption names the
assignment's id. A `deployIfNotExists` assignment evaluates new resources from the moment it exists
and existing ones only when a **remediation task** runs, which this set does not create (a
remediation is an operation; `avm/ptn/policy-insights/remediation` does it in Bicep, `az policy
remediation create` on the command line).

Role assignments on a fresh identity propagate in a minute or two; the Terraform module waits
(`time_sleep`) before it assigns the roles, and an authored render puts a `time_sleep` between the
identity and the role assignment.

A `Deny` assigned at the same time as the resources it would deny races them. The assignment is
rendered in its own root or applied first; a policy root that also holds the workload fails the
first apply in production and succeeds the second, which is the symptom of the race.

## Pitfalls

**The Bicep pattern module defaults the identity to `SystemAssigned`.** Every `Deny` and `Audit`
assignment rendered through it gets an identity it never uses, and the identity is a regional object
that needs the location. `identity: 'None'` is written on every call that has no `deployIfNotExists`
or `modify`.

**The Terraform module requires `azurerm` 4.x.** `avm-ptn-policyassignment` pins `azurerm ~> 4.0`
beside `azapi ~> 2.12` and `time`; a root on 5.x renders the authored `azurerm_*_policy_assignment`
resources instead, which carry every decision but `definition_version`. In 5.x the
management-group-scoped initiative is `azurerm_management_group_policy_set_definition`, not
`azurerm_policy_set_definition` with a group argument.

**`enforce` is a bool in the `azurerm` resources and an enum everywhere else.** `enforcement_mode:
DoNotEnforce` renders `enforce = false`; the test asserts the bool.

**The `Allowed locations` list must contain the deployment's own region and `global`.** A list that
omits the region denies the deployment that assigned it; one that omits `global` denies every Front
Door, Traffic Manager profile and DNS zone. The list is computed from `location` and the residency
answer, written out, and checked before the render.

**`Require a tag on resources` takes one tag.** One assignment per tag name; the built-in denies a
resource created without the tag, including one created by another pipeline, which is the point and
the first ticket.

**Not-scopes hide, exemptions show.** A not-scope removes resources from the compliance view; an
exemption lists them as exempt with a reason and an expiry. `not_scopes` is the platform's carve-out
tool, `exemptions` the workload's, and `exemption_expiry_required` keeps the holes from outliving
their reason.

**A custom definition is content.** `policies/<name>.rule.json` is read at plan time; a change to
the file changes the definition in place, and a definition in use by an assignment cannot be
deleted. A rule with a wrong `if` denies everything in the scope: the governance team reviews the
file, and a `DoNotEnforce` first assignment shows what it would deny.

**Rights.** Writing an assignment needs `Resource Policy Contributor` at the scope; one with an
identity also needs `User Access Administrator` (or `Role Based Access Control Administrator` with
a condition) at the scope to assign the identity's roles; a management-group assignment needs both
at that group. The handover lists them.

## Not covered here, and why

Remediation tasks, Defender for Cloud's standards and regulatory-compliance assignments, attestations,
Microsoft Purview policies, the ALZ policy set as a whole (`avm-ptn-alz`, `avm/ptn/alz/empty`), and
the authoring of policy rules each carry decisions of their own; a request for one is said out loud,
not improvised. The activity-log export that carries policy events to a workspace is the platform's
(`observability_ownership`).
