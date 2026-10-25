# App Service - what the question set cannot express

## Fixed at creation

- **The OS of the plan.** An app cannot move between a Linux and a Windows plan; it is
  redeployed.
- **Zone redundancy.** Set when the plan is created. Turning it on later is a new plan.
- **The name.** It is the public hostname (`<name>.azurewebsites.net`) and must be unique
  across Azure, so a name from the naming convention can still collide. With
  `auto_generated_domain_name_label_scope` the hostname gains a hash and the collision
  goes away - at the price of a hostname nobody can guess, which breaks anything that
  hard-codes it.
- **The region of a plan, and with it every app on it.**
- **A delegated subnet is exclusive to one plan.** The delegation to
  `Microsoft.Web/serverFarms` cannot be shared, and removing it from a subnet that still
  carries an integration fails.

## Ordering

The plan, then the site; the integration subnet and its delegation before the site; the
workspace before the diagnostic settings. In a spec with `composition`, the module holding
the site `needs` the plan, the network and the workspace. A private endpoint is created by
the site's module and needs the subnet, not the other way round.

## Pitfalls

**Inbound and outbound are two features.** The private endpoint is for traffic *to* the
app; regional VNet integration is for traffic *from* it. An app with only the endpoint
cannot reach a private database, and the failure is a timeout in the app. The two are
`public_network_access`/`private_endpoint_subnet` and `vnet_integration`/`integration_subnet`
in the question set, and a review that sees one without the other should ask.

**The Kudu/SCM site is a second front door.** It has its own access restrictions, its own
TLS minimum and its own basic-authentication switch. A private endpoint closes both
through the one `publicNetworkAccess`, but a public app with an allowlist must apply the
list to SCM too - `scm_use_main_ip_restriction` does that without a second list.

**Basic authentication is two switches.** FTP and SCM are separate; setting one leaves
the other open. The AVM Terraform module's SCM default is `true`.

**`always_on` and the 20-minute unload.** Off, the app is unloaded after idle and the next
request pays the cold start. Background work stops with it.

**Zone redundancy needs instances.** Two at least, and a Premium v3 size; a Basic size with
`zone_balancing_enabled` left at the module's default `true` fails the plan.

**`critical` is not a second region.** App Service has no cross-region mode. The answer
buys three instances in three zones; a regional failure is survived by a second deployment
behind a global front door, which is a pattern.

**Health checks replace instances.** A health-check path that returns anything but 2xx on
every instance - a 404 from a path that does not exist - marks the whole plan unhealthy.
That is why the default is empty.

**Settings are not secrets.** App settings are visible to anyone with read on the site.
A secret is a Key Vault reference (`@Microsoft.KeyVault(...)`) resolved with the app's
identity, which needs the role before the first start - the reason `user_assigned` exists
as an option.

**Log category names are the platform's.** `AppServiceHTTPLogs` and its siblings are
checked against `az monitor diagnostic-settings categories list --resource <site id>`
before a render; a wrong name fails the diagnostic setting at apply, not the site.

**A shared plan shares everything but the app.** Two sites on one plan draw on the same cores
and memory, the same instance count, the same zone setting and the same VNet integration subnet;
deployment slots and scale-out count against that capacity too. A plan sized for one app is
undersized for two, and the symptom is the second app's deploy slowing the first. The plan's
size is the owner's decision (`plan: own`); the second app's `plan: shared` names the owner and
nothing else about hosting.

## Not covered here, and why

Deployment slots, autoscale, custom domains and certificates, Easy Auth, backups and
Application Insights each carry decisions of their own. They are listed as boundaries
and have no question set yet; a request for one is said out loud, not improvised.
