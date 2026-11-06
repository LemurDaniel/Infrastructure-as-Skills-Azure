# Budget - what the question set cannot express

## What a budget is, and what it is not

A budget is a line in Cost Management that the resource group's costs are measured against, plus
up to five notifications. It **costs nothing and stops nothing**: a stage past its amount keeps
running and keeps being billed. Say so in the account before sign-off - a customer who hears
"budget" often expects a cap. Spend is stopped only by an action, a runbook or Logic App the
action group starts, and that is a design decision of its own.

## Fixed at creation

- **The scope.** The resource group it watches. Another scope is another budget.
- **The name.** Unique per scope; a renamed budget is a delete and a create, and its history in
  the portal starts again.
- **The start date** (`time_period.start_date` is ForceNew in `azurerm`). It must be the first
  day of a month and may not lie before the current month when the budget is created. It is not a
  decision: the render takes the first day of the month of the first deployment and keeps it
  (Terraform: `plantimestamp()` with `ignore_changes`; Bicep: a value in each stage file). A
  literal date in the template breaks the first deployment of a stage added months later.

## Ordering

The action group before the budget: the budget carries its id in every notification. The
resource group exists before both. Nothing depends on the budget.

## Pitfalls

**Cost data is late.** Usage reaches Cost Management with a delay of up to a day, so an
`Actual` threshold is never an instant alarm. A runaway resource is caught by a metric alert;
the budget catches the month.

**The amount is in the billing account's currency.** The template carries no currency. 500 is
euros on a euro account and dollars on a dollar account; write the currency into the account
before sign-off, not into the spec.

**Five notifications at most per budget.** `actual_thresholds` and `forecast_thresholds`
together; the API refuses a sixth. Each notification needs at least one recipient - an action
group, an e-mail or a role - or the deployment fails.

**The forecast needs history.** For the first days of a new stage there is nothing to project
from, and a forecast notification may fire early or not at all.

**Role recipients follow the role assignments.** `Owner` on the group means every owner, also
one inherited from the subscription - in a landing zone that can be the platform team. That is
usually wanted; where it is not, the role list is emptied and the action group carries it.

**Budgets are an operations object, not a cost estimate.** An amount below what the design
costs at rest notifies every month from the first day; compare it with the estimate before
sign-off.

## Not covered here, and why

Subscription and management group budgets (the platform's), budgets filtered by tag or meter,
cost anomaly alerts and scheduled cost exports each carry decisions of their own and have no
question set; a request for one is said out loud, not improvised.
