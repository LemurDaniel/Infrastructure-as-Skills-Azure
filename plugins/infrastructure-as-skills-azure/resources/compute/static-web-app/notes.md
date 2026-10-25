# Static Web Apps - what the question set cannot express

## Fixed at creation

- **The hostname and its partition.** The default hostname
  (`<generated>.<partition>.<n>.azurestaticapps.net`) is assigned at creation and cannot be
  chosen; a private endpoint's DNS zone depends on the partition. Recreating the app changes the
  hostname and the zone with it.
- **The region.** The app's metadata and managed functions live there; the offered regions are a
  short list.
- **The plan can move** (`Free` to `Standard`), but a private endpoint exists only on
  `Standard`, so a downgrade removes it first.

## Ordering

The app, then its private endpoint, then the DNS zone for the endpoint (the app's partition id is
only known after the app exists), then the first deployment of content. Custom domains need the
app's default hostname for their CNAME and come after.

## Pitfalls

**A private site is deployed to from inside the network.** With `public_network_access: disabled`
the content upload (`swa deploy`, the GitHub or Azure DevOps task) goes to the app's endpoint
too. A hosted runner outside the network cannot publish; a self-hosted one inside can. A
decision for the pipeline, not for this set.

**The private DNS zone cannot be pre-provisioned.** It carries the app's partition id, so a
platform that creates its `privatelink` zones up front has none for this service. With
`private_dns_records: policy` the policy has to create the zone and the record; with `deployment`
the zone is created after the app. **The Bicep module creates a zone by default**
(`createPrivateDnsZone: 'Enabled'`) as soon as a private endpoint is given, and links it to a VNet
- it is switched off here, because the platform owns zones.

**The modules disagree on defaults.** Public access (Terraform on, Bicep unset and disabled only
with a private endpoint), preview environments (both on), the SKU (both `Free`). Every decision
is written on the call.

**The deployment token is a secret and the Terraform module exports it.** `api_key` is an output
of the module and so lands in state. Read the token at deploy time (`az staticwebapp secrets
list`) in the pipeline rather than wiring the output anywhere; where the code does not need the
token, treat the state as holding a deployment credential.

**Preview environments are public copies of unreviewed work.** On a public app each pull request
gets an address anyone with the URL can open. Off by default here; where they are wanted, basic
authentication or the company login goes in front (not rendered).

**Authentication and routes are content.** Who may open which page, which login providers exist
and which routes are public are decided in `staticwebapp.config.json` in the repository, not in
Azure configuration. A "private site" in the Azure sense (no public endpoint) and a "protected
site" (login required) are different features; asking for the second does not need this set.

**No diagnostic setting.** The AVM modules expose no diagnostic settings for the service in
either target, so guardrail 5 ("every resource routes diagnostics somewhere") cannot be met at
the resource; a backend with managed functions logs through Application Insights, which is its
own resource. The handover names the gap.

**The Terraform module is `azurerm`-based and on 4.x.** It requires `azurerm ~> 4.0, < 5.0`; a
root calling it cannot be on 5.x.

## Not covered here, and why

Custom domains and certificates, authentication and route rules, basic authentication for preview
environments, linked backends (Functions, App Service, Container Apps), the app settings of
managed functions, repository linking and the enterprise-grade CDN each carry decisions of their
own and have no question set; a request for one is said out loud, not improvised.
