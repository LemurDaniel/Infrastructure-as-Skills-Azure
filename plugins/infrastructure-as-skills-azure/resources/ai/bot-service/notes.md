# Azure Bot - what the question set cannot express

## Fixed at creation

- **The app identity type and the app id.** `msaAppType`, `msaAppId` and the MSI reference are
  create-only; switching from a registration to a managed identity is a new bot.
- **The name.** Global (the bot handle); the Direct Line and token hostnames derive from it.
- **The location** (`global`; a regional bot is a different resource with a different endpoint
  set).

## Ordering

The user-assigned identity (identity set), the bot application with that identity assigned and
listening on `/api/messages` (its own set), then the bot with `messaging_endpoint` pointing at
it, then the channels, then the Teams app manifest and the Direct Line secrets or token flow on
the application team's side. For a private bot: the two private DNS zones, the two private
endpoints, and the application's VNet integration so its outbound to the Bot Framework also goes
the private way. The workspace before the diagnostic setting.

## Pitfalls

**There is no Bicep module.** `avm/res/bot-service/bot-service` is `Proposed` and unpublished;
Bicep renders authored resources and the spec records the forced departure. The Terraform
module exists and is young (0.6.0 at first publication year); its inputs are re-read per render.

**`MultiTenant` is the modules' default and the platform's refusal.** New bots cannot be created
multi-tenant; both defaults are overwritten. The managed-identity type is the one with nothing to
rotate.

**A private bot is a Direct Line bot.** `public_network_access: disabled` with the `Bot` and
`Token` endpoints serves only Direct Line (and Web Chat built on it) clients that reach the
private endpoints; Teams, Slack, e-mail and Microsoft 365 reach the bot through the public Bot
Framework and need `enabled`. The set forces it from `channels`. The application must also be
reachable *by* the service: a private application endpoint works only in the isolated Direct
Line model, where the application's outbound to the service goes through the same endpoints.

**Keys off means tokens from the application.** With `disableLocalAuth` a Direct Line client
cannot connect with the channel secret; the application exchanges its identity for a Direct Line
token and hands it to the client (enhanced authentication). A static web page with the secret
embedded is the case that cannot, and is a named departure.

**The customer-managed key is read by a Microsoft principal.** `Bot Service CMEK Prod` needs
`Key Vault Crypto Service Encryption User` on the vault, with soft delete and purge protection
on; the vault's role list in the handover names it. The bot takes the key URL, not an id.

**Developer Application Insights fields take an API key.** The bot resource's
`developerAppInsights*` properties exist for the portal's analytics blade and need an API key
created on the component; the set leaves them out - the application reports through its own
connection string and the bot's own record is `BotRequest`.

**Channel settings are not infrastructure.** The Teams channel's calling options, the Direct Line
sites and their trusted origins, the Slack client credentials: content of the application team,
changed in the portal or by their pipeline; a template that owns them overwrites their work on
the next deployment.

**Log category names are the platform's.** `BotRequest` today; checked against
`az monitor diagnostic-settings categories list --resource <bot id>` before a render.

## Not covered here, and why

The bot application and its hosting, app registrations (identity team), Teams app manifests and
publication, Direct Line Speech, Copilot Studio agents, Bot Framework Composer deployments, QnA
and LUIS (retired), regional bots and network security perimeters have no question set; a request
for one is said out loud, not improvised.
