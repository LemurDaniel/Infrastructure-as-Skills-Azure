# Subscription vending - what the question set cannot express

## A platform run, not a workload deployment

A workload lands in a subscription the platform vended (guardrails, section 0): the stage file
carries `subscription_id`, and nothing in the workload's code creates or touches the subscription.
This set is for the **platform run** that vends them - one alias per stage, each billed to a scope
and placed under a management group - and for an organisation with a billing account and no
platform. `subscription_ownership: platform` (the default) renders nothing.

The sub-vending patterns (`Azure/lz-vending/azurerm`, `avm/ptn/lz/sub-vending`) can also build the
spoke network with its hub peering, NSGs, route tables, a budget, identities with federated
credentials and resource groups. This set switches all of that **off** on purpose: the network is
the `virtual-network` set's, so the address space has one owner that the workload's later renders
agree with; budgets and identities are their own sets. A vending run that also builds the spoke is a
second source of truth for the workload's network.

## Fixed at creation

- **The billing scope and the workload type.** An offer cannot change afterwards; a `DevTest`
  subscription that goes to production is recreated as `Production` and the resources moved.
- **The alias.** It is the idempotency key; a changed alias is a second subscription.
- **The tenant.** A subscription belongs to the tenant it was created in; moving it is a
  transfer, not an update.

The display name, the management group (a move) and the tags change in place.

## Ordering

The management group (`management-group` set, or the platform's) and the billing rights first.
Then the alias; the subscription id is known only after it - the modules output it and wait
(`wait_for_subscription_before_subscription_operations`, `managementGroupAssociationDelayCount`)
before the management group association, the role assignments and the provider registration,
because a fresh subscription is not visible to RBAC for a minute or two. Then everything that needs
the id: the workload's stage file gets it, the `policy` set at subscription scope, Defender. The
inherited policies apply from the first evaluation after placement, so a subscription placed under
*corp* denies a public endpoint from its first deployment.

## Pitfalls

**Rights nobody in a workload team has.** Creating an alias needs `Enrollment account owner` (EA),
`Azure subscription creator` on the invoice section (MCA) or the partner's rights (MPA) on the
billing scope, plus `Management Group Contributor` on the target group and the right to write role
assignments at the new subscription. The handover lists them; the pipeline identity of the platform
run holds them, the workload's never does.

**The modules default resource-provider registration differently.** The Bicep pattern registers a
long built-in list when `resourceProviders` is left out - through a deployment script with its own
storage account, identity and virtual network in the new subscription - and `{}` registers none. The
Terraform module registers nothing unless `subscription_register_resource_providers_enabled` is
true. The list is always written, and empty means none in both.

**The Terraform shapes cancel on destroy.** `azurerm_subscription` and the module's `azapi` alias
cancel the subscription when removed; the module also tries to delete `NetworkWatcherRG` with
`az`. `cancel_on_removal: false` (the default) renders `prevent_destroy` on the authored resource and
the provider's `prevent_cancellation_on_destroy` feature; for the module it is a handover line,
because the module has no such switch. A cancelled subscription is deleted after ninety days and
can be reactivated before that.

**The Terraform module is not under the AVM name.** The index lists `avm-ptn-alz-sub-vending` as
Available with a repository that is not published; the module that exists is
`Azure/lz-vending/azurerm` (the index's alternative name "Azure Landing Zones - Sub vending"),
at major 7. It has no `azurerm` requirement at all - `azapi ~> 2.5` and `time` - so it sits in any
root, 4.x or 5.x.

**The Bicep pattern deploys at management group scope** and needs the resource providers' deployment
script to run somewhere: `deploymentScriptLocation` is the deployment's region. The alias itself is a
tenant resource (`scope: tenant()` in the authored form).

**`DevTest` is a term, not a feature.** The reduced rates come with "no production use" in the
agreement; a `DevTest` subscription that runs production is a licensing finding, not a technical
one. Production stays `Production` whatever the savings answer.

**Tags on the subscription** are `context.tags`; the Bicep module merges them (existing keys are
overwritten, others kept), the Terraform module sets them on the alias.

## Not covered here, and why

The spoke network, hub peering, NSGs and route tables (the network sets), budgets and cost alerts,
user-assigned identities with federated credentials (the `user-assigned-identity` set), resource
groups (the deployment set), Defender plans (`defender-for-cloud`), the activity-log export, PIM
eligible assignments, cross-tenant creation (`subscriptionTenantId`, `subscriptionOwnerId`) and the
cancellation or transfer of a subscription each carry decisions of their own; a request for one is
said out loud, not improvised.
