# Automation account - what the question set cannot express

## Fixed at creation

- **The name and the region.** A different name or region is a new account; job history,
  assets and webhooks of the old one do not move.
- **Webhook URLs.** The token is shown once, at creation, and cannot be read back. A webhook
  recreated by a deployment is a new URL that every caller has to be given again.
- **Nothing else.** The tier, public access, local authentication, the identity and the
  encryption key are changed in place.

## Ordering

1. The user-assigned identity, with its roles on what the runbooks manage and, for
   `customer_managed`, get, wrap and unwrap on the key - before the account, so the first
   scheduled job does not fail on a missing grant.
2. The key, in a vault with soft delete and purge protection.
3. The account, its private endpoints and its diagnostic setting.
4. The content - runbooks, modules, schedules, job schedules - from the automation team's
   repository. A job schedule references a runbook and a schedule that must already exist.
5. Hybrid workers: the VM with the Hybrid Worker extension, then the group membership.

## What runs where

| Where a job runs | Reaches | Needs |
|---|---|---|
| Azure's sandbox (no worker group) | Public endpoints only; never the private network | Nothing beyond the identity's roles |
| An extension-based hybrid worker | What the worker's subnet reaches - private endpoints, on-premises | A VM, the extension, `DSCAndHybridWorker` endpoint when public access is disabled |

A runbook that must reach a private endpoint (a database, a key vault with public access
disabled) runs on a hybrid worker. In a sandbox it fails with a name-resolution or a
connection error, not with an access error, which is why it is misread as a role problem.

## Pitfalls

**Local authentication off breaks webhooks.** With `disableLocalAuth` a webhook returns an
error and starts nothing. The alternative for a caller that can hold an identity is starting
the job through ARM (`Start-AzAutomationRunbook`, the REST `jobs` endpoint).

**The modules disagree on three defaults.** Terraform leaves local authentication on and public
access off; Bicep turns local authentication off and leaves public access unset (open unless
private endpoints are given). Every decision is written on the call.

**Contributor on the account is the identity's rights.** Anyone who can edit a runbook can run
code as the account's identity; the review of `role_assignments` is a review of the identity's
roles, too.

**Runbook output is logged.** `JobStreams` sends what a runbook writes to the workspace - a
`Write-Output` of a secret ends up there. Runbooks read secrets from Key Vault and never print
them.

**Linked workspaces are a retired pattern.** The Bicep module still offers
`linkedWorkspaceResourceId` and `gallerySolutions` for Update Management and Change Tracking;
both solutions ran on the retired Log Analytics agent. Leave them unset - patching is a
maintenance configuration, diagnostics are a diagnostic setting.

**Two private DNS records, one zone.** Both sub-resources resolve in
`privatelink.azure-automation.net`; the webhook record is per account, the hybrid worker record
per region. A zone group managed elsewhere (policy) must cover both.

## Not covered here, and why

Runbooks, schedules, webhooks, modules, variables, credentials, certificates and connections
are content, not infrastructure. Hybrid worker groups and their registration are wiring of an
account and a VM, owned by a pattern. State Configuration (DSC), Update Management and Change
Tracking are retired or replaced and have no question set; a request for them is pointed at
Machine Configuration, Azure Update Manager with a maintenance configuration, and Change
Tracking on the Azure Monitor agent.
