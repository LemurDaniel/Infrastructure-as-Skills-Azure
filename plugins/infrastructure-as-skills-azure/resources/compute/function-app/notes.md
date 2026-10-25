# Function App - what the question set cannot express

## Fixed at creation

- **The plan type** (Flex Consumption or Elastic Premium) and, with it, the OS. A function app
  does not move between plan types; it is redeployed.
- **Zone redundancy of the plan.** On Flex it needs a region that advertises the
  `FCZONEREDUNDANCY` capability; the plan module fails early where it is missing.
- **The name.** It is the public hostname (`<name>.azurewebsites.net`) and global.
- **The region of a plan, and with it every app on it.**
- **A delegated subnet is exclusive to one plan.** The delegation cannot be shared, and removing
  it from a subnet that still carries an integration fails.

## Ordering

The host storage account and its container, the user-assigned identity and its blob roles on the
account, the integration subnet and its delegation, the plan, then the app, then the diagnostic
setting and the roles *of* the app. The app reads its storage as it starts: a role granted at
the same apply is usually not yet effective, and the first start fails.

## Pitfalls

**The host storage account is a dependency with its own network.** If the account's firewall is
closed - which the storage set does by default - an app without VNet integration cannot start,
and the failure reads as a host error. The account must be reachable from the integration
subnet, by service endpoint or private endpoint, before the app exists.

**Two storage connections on Flex.** `AzureWebJobsStorage` is the host's own (function keys,
timer locks, trigger metadata); the deployment connection reads the package from the blob
container. They are configured separately (`storage_uses_managed_identity` and
`storage_authentication_type` in Terraform) and setting one does not set the other.

**Identity-based host storage is not retroactive.** Omitting `AzureWebJobsStorage` does not
delete it from an app that already has one; an existing app keeps its stale connection string
until it is removed out of band.

**Inbound and outbound are two features.** The private endpoint is for traffic *to* the app;
regional VNet integration is for traffic *from* it, including to the host storage. See
`vnet_integration`.

**The delegation depends on the plan.** Flex Consumption delegates the integration subnet to
`Microsoft.App/environments` (minimum /27), Elastic Premium and App Service plans to
`Microsoft.Web/serverFarms` (minimum /28) - Microsoft Learn, functions-networking-options. A
subnet delegated for the other kind cannot be reused.

**Cold starts are the price of scaling to zero.** With no always-ready instance the first call
after idle waits for an instance to start. Always-ready instances are billed at their baseline.

**Scale-out is a flood against whatever is downstream.** `max_instance_count` is the guard; a
queue trigger with a large backlog scales out until it reaches it.

**Settings are not secrets.** App settings are visible to anyone with read on the app. A secret
is a Key Vault reference resolved with the identity named by `key_vault_reference_identity`,
which needs its role before the first start.

**Log category names are the platform's.** Checked against `az monitor diagnostic-settings
categories list --resource <app id>` before a render; they can differ between Flex and Premium.

## Not covered here, and why

Triggers, bindings and function code, deployment slots, custom domains and certificates, Easy
Auth, Durable Functions storage options, the classic Consumption plan, Functions on a shared App
Service plan, Logic Apps (Standard) and Application Insights itself each carry decisions of
their own and have no question set here; a request for one is said out loud, not improvised.
