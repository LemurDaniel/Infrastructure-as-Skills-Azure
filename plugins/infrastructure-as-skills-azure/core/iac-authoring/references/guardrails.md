# The guardrails every default comes from

The rules that hold across every resource, so no question set has to restate them and no
two restate them differently. A resource's `questions.yaml` sets its defaults
*from* these rules; this file is where the reasoning lives. Read it before choosing a
default, before justifying one, and when a resource seems to need an exception.

They are **not** the Azure portal's defaults: the portal ships public network access,
shared-key auth and anonymous blob access enabled, and inheriting that posture is how an
exposure finding happens.

## 0. Platform model: with or without a landing zone

The plugin authors a **workload**, never the platform around it. Whether such a platform
exists is the customer's answer (`landing_zone_exists`), and the default is that it does
not: `landing_zone: standalone` - the deployment owns its network, its private DNS zones and
its Log Analytics workspace, and is private all the same.

Where there is one, the workload goes into an **application landing zone** - one subscription
under the *Landing zones* management group of the Cloud Adoption Framework's
[Azure landing zone](https://learn.microsoft.com/azure/cloud-adoption-framework/ready/landing-zone/)
architecture - and the platform around it belongs to someone else:

| Platform part | Where it lives | What the plugin does with it |
|---|---|---|
| Hub network, firewall, gateways, DNS resolver | Connectivity subscription | Peers a spoke to it — never creates or changes it |
| Private DNS zones (`privatelink.*`) | Connectivity subscription | References them, or leaves the records to policy — never creates them |
| Central Log Analytics workspace | Management subscription | Sends diagnostics to it — never creates it |
| Management groups, policy and role assignments | Tenant root and below | Works within them — never assigns them |
| Subscriptions | Subscription vending | Expects one — never creates it |

There the platform settles three things for every resource: `network_ownership: create`
builds a **spoke**, `private_dns_ownership: platform`, and `observability_ownership:
reference` - the values `deployment.yaml` holds for a landing zone, which `standalone`
pre-answers otherwise (below). "Nothing exists yet" from a user describes their
workload, not the platform; a run does not read it as licence to build hub
infrastructure.

**Exposure and platform decide the archetype.** `landing_zone_exists` and `network_exposure`
are asked; `landing_zone` is derived from them (`corp` for a private workload, `online` for a
public one) and pre-answers the network:

| `landing_zone` | Meaning | Pre-answers |
|---|---|---|
| `standalone` | **No landing zone** (`landing_zone_exists: no`). Central parts exist only where a `central_*` answer says so | per decision, unless its `central_*` answer is `yes`: `network_ownership: create` (standalone, not a spoke), `private_dns_ownership: deployment` (zones and their records created here), `observability_ownership: create`; a `yes` references that one part and leaves the rest as listed |
| `corp` | Private workload (`network_exposure: private` or `private_with_exceptions`), connected to the hub | `network_ownership: create` (spoke) |
| `online` | Internet-facing workload (`network_exposure: public`), not connected to the hub | public with a firewall allowlist (step 3 of the [posture ladder](#2-network-exposure)), `network_ownership: none` unless a private backend needs one |
| `sandbox` | Experiments, no hub, looser policy | `network_exposure: public` allowed, `network_ownership: none`; `environments` containing `production` is refused |

A user statement overrides a pre-answer, recorded as `overridden` — a corp workload with
one internet-facing endpoint is `private_with_exceptions`, not `online`.

`standalone` keeps every other guardrail. It moves ownership, not posture: without a platform
the deployment owns its DNS zones and its workspace, and is still private by default. It
also has no policy to lean on — nothing denies a public endpoint and nothing writes DNS
records — so the generated code has to do what the platform would have done.

**Platform policies act on what the workload deploys.** ALZ assigns `Deny` policies (public
network access, for instance) that make a non-compliant deployment fail, and
`DeployIfNotExists` policies that add resources after the deployment — most importantly
the DNS records for private endpoints. Whatever a `DeployIfNotExists` policy deploys, the
generated code must not deploy as well: two writers to the same record means a plan that
never stops showing drift, and the policy re-applying what the code removed.
`private_dns_records` decides which writer owns the records.

The plugin never builds the platform. Hub, management groups, policy assignments and
subscription vending belong to the ALZ accelerator modules; a workload deployment that
creates any of them is a second source of truth for the platform.

Where an organisation has no landing zone platform, that is `landing_zone: standalone` — an
answer, not an exception, so its consequences are pre-answers rather than `overridden`
values.

### Stages

One code base is deployed through a stack of stages — `development`, `test`, `production`
by default — each from its own parameter file and its own state, and nearly every system
starts in development; a request that names only production names the production stage
of that stack. The stages are separated by **subscription** by default, which is what a
landing zone platform vends and where quotas, budgets, policy and RBAC stop; a resource
group per stage in one subscription is the lesser form for an organisation that cannot
get subscriptions. What differs per stage by nature — address ranges, subnet prefixes,
the subscription, the resource group, a referenced hub or workspace — is a parameter with
its value in the stage's file, never a literal in the template.

Decisions are the same in every stage: parity is what the stack exists for. The one
relaxation is cost: a question's `non_production_default` - a smaller SKU, no zone
redundancy, fewer instances, cheaper replication, shorter log retention - applies in every
stage but production while `non_production_savings` is enabled, and it never touches
security, exposure, identity, DNS or compliance, because a development stage that is less
secure than production is where the breach happens. A customer who wants the stages
identical says so.

## 1. Naming and tags

Never hardcode a resource name, and never hand-write a tag per resource.

**Names follow the plugin's convention unless the customer specifies another.** The
convention is [naming.default.yaml](../../iac-rendering/references/naming.default.yaml) —
CAF abbreviations, AVM region codes, `<TYPE>-<LOCATION>-<ENVIRONMENT>-<NAME>-<INDEX>` with
per-type patterns where Azure's limits force them (`stweprodpayments01`,
`kv-we-prod-payments-a1b2`). Every root gets a full copy as `naming.yaml` beside the spec on
the first run: Terraform's provider reads it, Bicep's name `var`s are generated from it.
From then on the convention is what the repository holds:

- **The customer's word wins.** A different pattern, abbreviation or environment code goes
  into their `naming.yaml` and the spec records `naming_convention: custom`. A repository
  that already has a naming file or a naming provider block keeps it.
- **No run overwrites `naming.yaml`**, and no run renames a deployed resource to match a
  newer default. Most Azure names are immutable; a changed name is a destroy.
- **No name outside the convention.** Not a literal in one template, not a suffix added by
  hand to dodge a collision. A second convention in one file is one nobody maintains.

Rendering per target is in [naming.md](../../iac-rendering/references/naming.md).

**Tags prescribe no content.** Which tags exist is an organisation's decision, not this plugin's. Take the set from the
repository — an existing `locals.tags`, a `var tags` in `main.bicep`, what the resources
already carry — and apply the same one. What the request names goes
into the spec's `context.tags`, which is then what every resource gets. Where neither the
repository nor the request has one, the tags stay empty: the render passes an empty set and
Phase 4 says so - not asked, not an open item, never invented. A tag set invented by a
generator is a tag set nobody queries.

The applying is the mechanical part: one merged local or variable, passed everywhere. A
resource with its own tag literal drifts from its siblings the first time the set changes.
How that looks per target is in the idiom files.

## 2. Network exposure

**Default to no public network access.** Every resource that can be reached privately is
generated that way, and public exposure is a decision somebody makes explicitly.

The posture ladder, in order of preference:

1. **Private endpoint** — the resource has no public surface. Costs an endpoint and a DNS
   zone entry, which is the price of the posture.
2. **Service endpoint / allowed subnets** — cheaper, but the resource is still publicly
   addressable and relies on an ACL to refuse traffic.
3. **Public with a firewall allowlist** — acceptable for a dev environment or where the
   consumer genuinely lives off-network. The allowlist must be enumerated; `0.0.0.0/0` in
   a firewall rule is not an allowlist.
4. **Public, unrestricted** — only with a stated reason recorded in the spec as
   `overridden`.

Private DNS zones are shared infrastructure. No resource that needs one creates it: in a
landing zone the platform owns them, without one the deployment creates each zone once, as a
`private-dns-zone` resource of its own (`private_dns_ownership`, [platform
model](#0-platform-model-with-or-without-a-landing-zone)) - two resources, or two
deployments, each creating `privatelink.blob.core.windows.net` is a conflict that only shows
up at apply time.

## 3. Identity over keys

**Managed identity and RBAC, not connection strings and access keys.** Where a resource
supports disabling local auth, disable it:

| Resource | The switch |
|---|---|
| Storage account | `shared_access_key_enabled: false` |
| Key Vault | `rbac_authorization: true` (not access policies) |
| App Service | FTP and SCM basic publishing credentials disabled; both switches, they are separate |
| Service Bus / Event Hub | local auth disabled |
| Cosmos DB | local auth disabled |
| SQL | Entra-only authentication |

A resource carries an identity only when it reaches another resource outward (customer-managed
key, storage, a data source, a backend); callers use their own identities, so a resource that
reaches nothing carries none. Where it does, system-assigned by default. Reach for user-assigned when an identity must outlive
a single resource or be shared across several — pre-assigning permissions before a resource
exists is the usual legitimate reason.

Role assignments are scoped as tightly as the consumer allows: the specific container or
secret, not the subscription. A role assignment at subscription scope in generated code is
a bug unless the resource genuinely operates subscription-wide.

## 4. Encryption

Platform-managed keys are the default, and that is not a compromise — they are encrypted,
rotated and free, and the operational burden of customer-managed keys is real.

Customer-managed keys are warranted when a compliance regime names them, or when key
revocation needs to be a capability you actually hold. Choosing them pulls in a Key Vault
with purge protection, an identity with wrap/unwrap, and a rotation story. If the spec
asks for CMK without those, the answer is incomplete rather than ready.

Encryption in transit is never negotiable: TLS 1.2 as the floor, HTTPS-only where the
resource has the switch.

## 5. Diagnostics

Every resource routes diagnostics somewhere. A resource with no diagnostic setting is
invisible exactly when someone needs to see it.

- **Destination**: a Log Analytics workspace by default. A storage account only for
  long-retention archival, and then alongside the workspace, not instead of it.
- **Categories**: audit categories always. `allLogs` in non-production and for anything
  handling regulated data; be deliberate in production where volume has a price.
- **Metrics**: `AllMetrics`, which is cheap.

The workspace is shared infrastructure, like DNS zones: in a landing zone the platform's, in
the management subscription, and referenced; without one created once by the deployment, as a
`log-analytics-workspace` resource of its own (`observability_ownership`, [platform
model](#0-platform-model-with-or-without-a-landing-zone)). No resource that sends diagnostics
creates it.

## 6. Exceptions

A guardrail that cannot be departed from gets worked around instead of discussed, which is
worse. So exceptions are allowed, and the cost is recording them:

- The spec records the value with `source: overridden` and a comment stating the reason.
- Generated code carries a comment at the departing attribute pointing at that reason.
- An exception in an earlier spec keeps its reason when the spec is extended, and is listed
  again at the sign-off - never applied silently because it was there before.

What is not allowed is a silent exception. If a generated resource departs from these rules
and nothing says why, that is the defect — not the departure.
