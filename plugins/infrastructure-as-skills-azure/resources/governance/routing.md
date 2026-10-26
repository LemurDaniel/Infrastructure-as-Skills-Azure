# Azure governance resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| policy, Azure Policy, policy assignment, initiative, policy definition, exemption, allowed locations, deny public access, require tags, Richtlinie, Richtlinienzuweisung, Ausnahme, Compliance | `policy/questions.yaml` | [notes](policy/notes.md) - scope-level; nothing renders by default (`policy_ownership: platform`); custom rules are content in `policies/` |
| management group, Management-Gruppe, MG, hierarchy, subscription placement, move subscription, Verwaltungsgruppe | `management-group/questions.yaml` | [notes](management-group/notes.md) - tenant scope; nothing renders by default (`management_group_ownership: platform`); the ALZ hierarchy is the `avm-ptn-alz` pattern, not this set |
| subscription, new subscription, subscription vending, sub vending, create subscription, Subscription anlegen, Abonnement, billing scope, enrollment account, DevTest | `subscription/questions.yaml` | [notes](subscription/notes.md) - a platform run only; a workload references `deployment.subscription_id` and this renders nothing (`subscription_ownership: platform`); network and budget come from their own sets |
| resource group, Ressourcengruppe, resource group split | see the deployment set's `resource_groups` group and [resource-groups.md](../../core/iac-rendering/references/resource-groups.md) | Not a set of its own - a deployment decision, one mode per role |
| lock, resource lock, CanNotDelete | `deployment.resource_lock` for the resources a spec owns | A standalone lock on a referenced resource has no set yet |
| budget, cost alert, Kostenlimit | *not yet written* | - |
| Automation Account, runbook, Maintenance Configuration, update management, patch schedule | *not yet written* | - |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers the landing zone, the subscription and the resource groups before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**The platform owns the scope above the workload.** Management groups, subscriptions and the
policies assigned to them are the landing-zone hierarchy's; a workload deployment lands inside
it and references what is there. Every set here opens with an ownership question
(`resolved_by: platform`, default `platform`) that renders nothing, and only a platform run or a
`landing_zone: standalone` deployment answers `deployment`.

**Scope, not resource group.** These resources deploy at tenant, management-group or
subscription scope: no resource group, usually no region, and a different permission to deploy
(`Management Group Contributor`, `Resource Policy Contributor`, the billing role). Bicep carries
the `targetScope`, Terraform the provider's tenant-level resources; the pipeline's identity needs
that scope before the run.

**Nothing here has resource logs.** The activity log of a group or subscription is exported by
a platform setting, not by a diagnostic setting of the set; none of the sets carries an
`observability` group and each `notes.md` says so.
