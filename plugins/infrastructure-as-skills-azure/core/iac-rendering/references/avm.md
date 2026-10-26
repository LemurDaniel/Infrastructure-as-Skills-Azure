# Rendering with Azure Verified Modules

Azure Verified Modules (AVM) are Microsoft's published, tested, versioned modules for
Terraform and Bicep — one resource module per Azure resource type, a pattern module per
common composition, both targets following one specification. **They are the primary
rendering target of this plugin.** A resource that has an AVM module renders as a call to
it; a resource that has none renders as authored code from the resource's own
`terraform.md` / `bicep.md`, and the spec says so.

The question sets do not change. The interview still resolves every decision, the spec
still records every value with its source, and the module is where those values land.
What changes is the shape of the output: a module call with the decisions as inputs,
instead of resources with the decisions as attributes.

## Why modules first, and what it costs

- **The hard parts of a resource are already implemented.** Private endpoints with their
  DNS zone groups, diagnostic settings per sub-resource, role assignments, locks,
  customer-managed keys with the identity dance — every AVM module implements the same
  shared interfaces for these, tested against Azure. The authored references in this repo
  reinvent each of them per resource, and that is exactly where the first render had its
  bugs (the account-level diagnostic setting that collects no blob logs, the private
  endpoint named after the index).
- **One contract across both targets.** The Bicep `privateEndpoints` array and the
  Terraform `private_endpoints` map are the same interface. A spec rendered twice lands on
  the same module surface, which is what makes the cross-backend diff small.
- **What it costs: a module does not expose every decision.** The Terraform storage module
  takes `public_network_access_enabled` as a bool, not the 5.x string; the Bicep workspace
  module defaults `dataRetention` to 365 where the guardrails say 30. Every module call is
  therefore rendered with the decisions **written out explicitly**, even where they match
  the module default — the module default is not the guardrail's default, and a module
  release can move it. A decision the module cannot carry at all is named in the handover
  (see *Gaps*), never dropped.
- **Versions move fast and are `0.y.z`.** Every AVM module today is pre-1.0; minor versions
  may break. The pin is always explicit and the lookup is always live (below).

## Which module

The module is resolved **here**, in the renderer, from the resource type the question set
names — never written into the spec (see
[spec.md](../../iac-authoring/references/spec.md#reusing-an-existing-module)). The
coordinate follows from the resource provider namespace and type:

| | Terraform | Bicep |
|---|---|---|
| Resource module | `Azure/avm-res-<namespace>-<type>/azurerm` | `br/public:avm/res/<namespace>/<type>:<x.y.z>` |
| Pattern module | `Azure/avm-ptn-<name>/azurerm` | `br/public:avm/ptn/<name>:<x.y.z>` |
| Example | `Azure/avm-res-storage-storageaccount/azurerm` | `br/public:avm/res/storage/storage-account:0.33.1` |
| Source of truth | [Terraform index](https://azure.github.io/Azure-Verified-Modules/indexes/terraform/) | [Bicep index](https://azure.github.io/Azure-Verified-Modules/indexes/bicep/) |
| Code | `github.com/Azure/terraform-azurerm-avm-res-<namespace>-<type>` | `github.com/Azure/bicep-registry-modules`, `avm/res/<namespace>/<type>/` |

The namespace and type are lowercased and, on the Bicep side, kebab-cased
(`operationalinsights-workspace` ↔ `operational-insights/workspace`). The index is the
only authoritative list; the two names do not always derive mechanically.

### Status decides whether it is used

The index carries a status per module. Read it before rendering:

| Status | What to do |
|---|---|
| `Available` | Use it. The default path |
| `Orphaned` | Published and working, but without an owner: use it, and say so in the handover — the next fix may be slow. The Terraform Key Vault module is in this state today |
| `Proposed` | Not published. Render authored code for that resource and record `implementation: authored` with `source: forced`, `forced_by: no AVM module for <type>` |
| `Deprecated` | Do not use. As `Proposed` |
| Not in the index | As `Proposed`. Say out loud that no module exists; do not guess a coordinate |

### Modules for the resources this plugin knows

Looked up on 2026-10-17. **Versions are a snapshot, not a pin to copy** — resolve the
current one before rendering (next section).

| Resource | Terraform module | Bicep module | Notes |
|---|---|---|---|
| Storage account | `avm-res-storage-storageaccount` v0.10.0 | `avm/res/storage/storage-account` 0.33.1 | Terraform module is AzAPI-based since 0.7 — see *Provider requirements* |
| Virtual network | `avm-res-network-virtualnetwork` v0.22.3 | `avm/res/network/virtual-network` 0.10.2 | Terraform module is AzAPI-based; subnets are a child module, usable alone for a referenced vnet |
| Log Analytics workspace | `avm-res-operationalinsights-workspace` v0.5.1 | `avm/res/operational-insights/workspace` 0.16.1 | Terraform module still requires `azurerm` **4.x** (`>= 4.36, < 5.0`) |
| App Service plan | `avm-res-web-serverfarm` v2.0.8 | `avm/res/web/serverfarm` 0.7.0 | Terraform module is AzAPI-based (`azapi ~> 2.4`); exposes only `name` and `resource_id` as outputs. Looked up 2026-10-18 |
| App Service (web app) | `avm-res-web-site` v0.24.1 | `avm/res/web/site` 0.24.0 | Terraform module is AzAPI-based (`azapi ~> 2.12`, `time`); `resource` output is the site. Looked up 2026-10-18 |
| Private endpoint | `avm-res-network-privateendpoint` v0.2.0 | `avm/res/network/private-endpoint` 0.12.1 | Rarely called directly — every resource module carries the interface |
| Key Vault | `avm-res-keyvault-vault` v0.12.0, **Orphaned** | `avm/res/key-vault/vault` 0.14.2 | Terraform module is **`azurerm`-based** (`>= 4.81, < 5.0`, plus `azapi`, `modtm`, `random`, `time`), takes `resource_group_name`. Module defaults diverge from the guardrails: SKU `premium` in both, `enableVaultForDeployment` true in Bicep, public access true in Terraform. Looked up 2026-10-23 |
| User-assigned identity | `avm-res-managedidentity-userassignedidentity` v0.5.3 | `avm/res/managed-identity/user-assigned-identity` 0.6.0 | Terraform module `azurerm`-based (`>= 4.60.0, < 5.0.0`). Looked up 2026-10-23 |
| Cosmos DB account | `avm-res-documentdb-databaseaccount` v0.11.0 | `avm/res/document-db/database-account` 0.21.1 | Terraform module `azurerm`-based (`~> 4.0`); **no input for data-plane role assignments**. The modules disagree on defaults: consistency (`BoundedStaleness` / `Session`), periodic backup redundancy (`Geo` / `Local`). Looked up 2026-10-23 |
| AI Search service | `avm-res-search-searchservice` v0.3.0 | `avm/res/search/search-service` 0.13.0 | Terraform module `azurerm`-based (`~> 4.0`). Modules disagree: replica count (1 / 3), local auth (on / off); both leave public access on. Looked up 2026-10-23 |
| AI Foundry / Azure OpenAI (Cognitive Services account) | `avm-res-cognitiveservices-account` v0.11.1 | `avm/res/cognitive-services/account` 0.19.1 | Terraform module is AzAPI (`parent_id`) **and** constrains `azurerm >= 4.17, < 5.0`. Neither module creates Foundry projects. Bicep `deployment`/`project` child modules are `Proposed`. Looked up 2026-10-23 |
| Container Registry | `avm-res-containerregistry-registry` v0.8.0 | `avm/res/container-registry/registry` 0.13.1 | Terraform module `azurerm`-based (`>= 4.81, < 5.0`). Modules disagree: untagged retention (7 / 15 days), trusted-service bypass (`None` / `AzureServices`), export policy; Terraform leaves public access on. Looked up 2026-10-23 |
| Container Apps environment | `avm-res-app-managedenvironment` v0.5.1 | `avm/res/app/managed-environment` 0.16.0 | Terraform module needs `azurerm ~> 4.0` and `azapi`; many inputs deprecated for `vnet_configuration`, `zone_redundant`, `workload_profiles`. Looked up 2026-10-23 |
| Container App | `avm-res-app-containerapp` v0.9.0 | `avm/res/app/container-app` 0.23.0 | Terraform module AzAPI only. **Bicep defaults to external ingress, HTTP allowed, port 80**; Terraform to internal, HTTPS. Looked up 2026-10-23 |
| Function App | `avm-res-web-site` v0.24.1 (`kind = "functionapp"`, `function_app_uses_fc1`) | `avm/res/web/site` 0.24.0 (`kind: 'functionapp,linux'`, `functionAppConfig`) | Same module as App Service. Plan `FC1` zone redundancy needs the `FCZONEREDUNDANCY` capability. Looked up 2026-10-23 |
| Application Insights | `avm-res-insights-component` v0.5.0 | `avm/res/insights/component` 0.8.0 | Terraform module AzAPI only (`azapi`, `time`). Modules disagree: IP masking (`false` / `true` stores IPs), retention (90 / 365); both default public ingestion/query on and local auth off. Looked up 2026-10-23 |
| Network security group | `avm-res-network-networksecuritygroup` v0.6.0 | `avm/res/network/network-security-group` 0.5.4 | Terraform module AzAPI only. Looked up 2026-10-23 |
| Resource group | `avm-res-resources-resourcegroup` v0.4.0 | `avm/res/resources/resource-group` 0.4.4 | Rendered per role whose `resource_group_mode_<role>` is `create`; an `existing` group is only read. See [resource-groups.md](resource-groups.md) |
| Service Bus namespace | `avm-res-servicebus-namespace` 0.4.0 | `avm/res/service-bus/namespace` 0.17.1 | Terraform module `azurerm`-based (`~> 4.14`, no `azapi`). **Modules disagree on defaults:** SAS local auth (on / off), trusted-service bypass (off / on), public access (on / unset); both default to Premium and double encryption. No Terraform input for zone redundancy or geo-recovery. Looked up 2026-10-25 |
| Event Hubs namespace | `avm-res-eventhub-namespace` 0.1.1 | `avm/res/event-hub/namespace` 0.15.2 | Terraform module AzAPI with `azurerm ~> 4.0`; no input for TLS minimum, double encryption, zone redundancy, consumer groups or geo pairing, and `network_rulesets` is documented as Premium-only. Bicep zone redundancy defaults to true. Looked up 2026-10-25 |
| Event Grid topic | `avm-res-eventgrid-topic` 0.1.1 | `avm/res/event-grid/topic` 0.10.0 | Terraform module AzAPI with `azurerm ~> 4.0`. Modules disagree on public access (`Disabled` / unset). Looked up 2026-10-25 |
| API Management service | `avm-res-apimanagement-service` 0.1.0 | `avm/res/api-management/service` 0.15.0 | Terraform module AzAPI with `azurerm >= 4.0, < 5.0`. **Modules disagree on the tier:** Terraform `Developer_1`, Bicep `Premium` with 3 units. Placeholder publisher name in Terraform. Looked up 2026-10-25 |
| Application Gateway | `avm-res-network-applicationgateway` 0.5.3 | `avm/res/network/application-gateway` 0.10.0 | Terraform module AzAPI with `azurerm >= 3.117, < 5.0` and Terraform `>= 1.12`. The firewall policy is a separate module in both targets. Bicep defaults to `WAF_v2` with a fixed capacity of 2. Looked up 2026-10-25 |
| Application Gateway WAF policy | `avm-res-network-applicationgatewaywebapplicationfirewallpolicy` 0.2.0 | `avm/res/network/application-gateway-web-application-firewall-policy` 0.3.0 | Terraform module `azurerm`-based (`~> 4.2`). Looked up 2026-10-25 |
| Front Door (Standard / Premium) | `avm-res-cdn-profile` 0.1.9 | `avm/res/cdn/profile` 0.20.0 | The CDN profile module carries Front Door. Terraform AzAPI with `azurerm ~> 4.0`, firewall policy inside the module; Bicep takes the policy from `avm/res/network/front-door-web-application-firewall-policy` 0.3.3. Response timeout 120 / 60. The Bicep `avm/res/network/front-door` module is **Deprecated**. Looked up 2026-10-25 |
| Backup vault (Data Protection) | `avm-res-dataprotection-backupvault` 2.0.9 | `avm/res/data-protection/backup-vault` 0.13.3 | Terraform module AzAPI with `azurerm >= 4.2, < 6.0` (works on 5.x). Soft delete is always on in the current API version. The Bicep module has no Resource Guard parameter. Looked up 2026-10-25 |
| Recovery Services vault | `avm-res-recoveryservices-vault` 1.3.3 | `avm/res/recovery-services/vault` 0.13.2 | Terraform module **AzAPI only** (no `azurerm`). Modules disagree on public access (on / off) and cross-region restore (on / unset); both default to geo-redundant storage. Looked up 2026-10-25 |
| SQL Managed Instance | `avm-res-sql-managedinstance` 0.3.1 | `avm/res/sql/managed-instance` 0.5.1 | Terraform `azurerm ~> 4.0`, `azapi ~> 2.4`; requires an administrator login and password even with Entra-only, backup storage LRS/ZRS/GRS only, zone redundancy default true, proxy override `Default`. Bicep: no `privateEndpoints` parameter, `diagnosticSettings` logs only, zone redundancy default false, proxy `Proxy`, backup `Geo`. Looked up 2026-10-26 |
| Data Factory | `avm-res-datafactory-factory` 0.2.0 | `avm/res/data-factory/factory` 0.13.0 | Terraform `azurerm >= 3.0, < 5.0`, `azapi ~> 2.4`; public access defaults **true**; private endpoints fixed to `dataFactory` (portal authored); no managed private endpoint and no Azure IR input. Bicep: `gitConfiguration` is the raw ARM `repoConfiguration`; `publicNetworkAccess` defaults to disabled only when endpoints are passed. Looked up 2026-10-26 |
| Purview account | none - `avm-res-purview-account` is **Proposed**; authored `azurerm_purview_account` on 5.x | `avm/res/purview/account` 0.10.0 | azurerm has no argument for the managed resources' public access (`azapi_update_resource`), public access and managed Event Hub default **true**. Bicep: one endpoint array per kind, managed Event Hub default Enabled, public access default NotSpecified. Looked up 2026-10-26 |
| Logic Apps (Standard site + plan, Consumption workflow) | `avm-res-web-site` 0.24.1 (`kind = "logicapp"`) + `avm-res-web-serverfarm` 2.0.8; `avm-res-logic-workflow` 0.1.2 | `avm/res/web/site` 0.24.0 (`kind: 'functionapp,workflowapp'`) + `avm/res/web/serverfarm` 0.7.0; `avm/res/logic/workflow` 0.6.0 | The workflow module is `azurerm`-based **`>= 4.21.1, < 5.0`**. **Gap:** for `kind = "logicapp"` the Terraform site module requires `storage_account_access_key` and always writes a key-based `AzureWebJobsStorage`, so identity-based host storage renders the site authored (azapi); the Bicep site module writes no logic-app host settings. Plan default `P1v2` is refused for logic apps. Looked up 2026-10-26 |
| Communication Services (+ Email Communication Service) | **none in the index** for `communicationServices`; `avm-res-communication-emailservice` 0.3.0 for the e-mail service and domains | `avm/res/communication/communication-service` 0.6.0; `avm/res/communication/email-service` 0.4.5 | Terraform: the communication resource is authored as `azapi_resource` `@2025-09-01` because `azurerm_communication_service` has no local-auth or public-access argument; the e-mail module is AzAPI (`azapi ~> 2.12`, Terraform `>= 1.11`). Bicep modules leave `disableLocalAuth` and `publicNetworkAccess` unset. Looked up 2026-10-26 |
| AI Services single-service account (Speech, Vision, Language, Document Intelligence, Content Safety, Translator, Custom Vision, Face) | `avm-res-cognitiveservices-account` 0.11.1 | `avm/res/cognitive-services/account` 0.19.1 | Same modules and pins as Foundry (AzAPI + `azurerm >= 4.17, < 5.0`). Modules disagree: local auth (TF on / Bicep off), outbound restriction (TF off / Bicep on); Bicep has no `allowedFqdnList` parameter. `F0` is one per kind per subscription. Looked up 2026-10-26 |
| Machine Learning workspace | `avm-res-machinelearningservices-workspace` 0.9.0 | `avm/res/machine-learning-services/workspace` 0.14.1 | Terraform module AzAPI with `azurerm >= 4.17, < 5.0`, **creates** storage, vault, insights and registry when their `resource_id` is null (always pass ids); no input for `v1LegacyMode` or computes; isolation default `Disabled`. Bicep requires `sku`, defaults public access `Disabled` and a system identity, leaves isolation unset, carries `computes`. Looked up 2026-10-26 |
| Azure Bot (Bot Service) | `avm-res-botservice-botservice` 0.6.0 | **`avm/res/bot-service/bot-service` is Proposed, unpublished** - authored `Microsoft.BotService/botServices@2022-09-15` is the Bicep primary | Terraform module AzAPI only (`azapi ~> 2.12`), defaults `sku F0`, `microsoft_app_type MultiTenant` (refused for new bots), streaming on, local auth on, public access on - all written. Looked up 2026-10-26 |
| Event Grid namespace | `avm-res-eventgrid-namespace` 0.1.2 | `avm/res/event-grid/namespace` 0.8.0 | Terraform AzAPI-based (`parent_id`), pins `azurerm ~> 4.0`, `azapi ~> 2.4`; writes `sku`/`capacity` but has no `isZoneRedundant`, no TLS minimum and no `topicSpacesConfiguration.state` (the MQTT broker needs an `azapi_update_resource`). Bicep writes zone redundancy and the MQTT state but has **no `sku`/`capacity`** and no TLS input. Both default public access `Enabled`. Terraform `max_delivery_count` default 30 vs service 10. Looked up 2026-10-26 |
| Event Grid system topic | none - `avm-res-eventgrid-systemtopic` is **Proposed**; authored `azurerm_eventgrid_system_topic` + `_event_subscription` on 5.x (endpoint args renamed `service_bus_queue_id`, `eventhub_id`, ...) | `avm/res/event-grid/system-topic` 0.7.0 | Bicep `location` defaults to the group's - written as the source's region or `global`; `eventSubscriptions` untyped. Looked up 2026-10-26 |
| Relay namespace | `avm-res-relay-namespace` 0.1.1 | `avm/res/relay/namespace` 0.8.0 | Terraform AzAPI-based, pins `azurerm ~> 4.0`; hybrid connections, WCF relays, auth rules and the network rule set are `//modules/<name>` submodules pinned beside the root. Bicep **`authorizationRules` defaults to RootManageSharedAccessKey** - pass `[]`; public access only via the `networkRuleSets` child. Both default public access `Enabled`; the type has no local-auth switch. Looked up 2026-10-26 |
| Public DNS zone | `avm-res-network-dnszone` 0.2.1 | `avm/res/network/dns-zone` 0.6.2 | Terraform module `azurerm`-based (`>= 3.71, < 5.0`), no location, lock, role-assignment or DNSSEC input, every record object repeats `resource_group_name` and `zone_name`; DNSSEC rendered as an authored `azapi_resource` `dnsZones/dnssecConfigs@2023-07-01-preview`. Bicep has `enableDnsSec`, lock, roleAssignments; record TTL default 3600. Neither has diagnostics. Looked up 2026-10-26 |
| Traffic Manager profile | `avm-res-network-trafficmanagerprofile` 0.1.1 | `avm/res/network/trafficmanagerprofile` 0.4.0 | Terraform module AzAPI only (`azapi ~> 2.12`, no location input), routing method, dns_config and monitor_config required, endpoints as three maps, no `resource` output. Bicep path is one word; defaults **Performance**, TTL 60, probe `http` on port 80 at `/`. Looked up 2026-10-26 |
| DDoS protection plan | `avm-res-network-ddosprotectionplan` 0.3.0 | `avm/res/network/ddos-protection-plan` 0.3.2 | Terraform module `azurerm`-based (`>= 3.116, < 5.0`). Neither module has diagnostics (the type has none). Looked up 2026-10-26 |
| Network Watcher / flow logs | `avm-res-network-networkwatcher` 0.3.2 | `avm/res/network/network-watcher` 0.5.1, child `avm/res/network/network-watcher/flow-log` 0.1.0 | Terraform module pins `azurerm ~> 4.0` plus `azapi ~> 2.0`; it **never creates the watcher** (`network_watcher_id/name` required) and the flow logs are `azapi_resource`s; the monitors input is `condition_monitor`. Bicep parent always declares the watcher (idempotent PUT in NetworkWatcherRG); flow-log retention default **365**. Looked up 2026-10-26 |
| Action group | `avm-res-insights-actiongroup` 0.1.0 | `avm/res/insights/action-group` 0.8.0 | Terraform module AzAPI only (`azapi ~> 2.12`; Terraform >= 1.11 once a webhook or function URL is set, write-only `sensitive_body`), takes `parent_id`, exposes `resource_id` only. Both modules default `use_common_alert_schema` to false per receiver. Looked up 2026-10-26 |
| Alert rule (metric / log query / activity log) | `avm-res-insights-activitylogalert` 0.1.0; `avm-res-insights-metricalert` and `avm-res-insights-scheduledqueryrule` are **Proposed** - authored on azurerm 5.x (`azurerm_monitor_metric_alert`, `azurerm_monitor_scheduled_query_rules_alert_v2`) | `avm/res/insights/metric-alert` 0.4.1, `avm/res/insights/scheduled-query-rule` 0.6.1, `avm/res/insights/activity-log-alert` 0.4.2 | Activity log alert Terraform module AzAPI only, `resource_id` only. Both targets default severity 3; Bicep metric alert defaults windowSize PT15M and scope = subscription. Looked up 2026-10-26 |
| Data collection rule (+ endpoint) | `avm-res-insights-datacollectionrule` 0.1.0, `avm-res-insights-datacollectionendpoint` 0.2.0 | `avm/res/insights/data-collection-rule` 0.11.0, `avm/res/insights/data-collection-endpoint` 0.5.1 | Terraform modules AzAPI only (`azapi ~> 2.4`), `parent_id`. **Terraform DCR module validates `kind` to Linux/Windows only** (Direct, AgentDirectToStore, WorkspaceTransforms render authored); Bicep DCR module has no AgentDirectToStore variant and **no `diagnosticSettings` parameter**. **Endpoint public access defaults disagree: Terraform `Enabled`, Bicep `Disabled`.** Associations are not an input of either module. Looked up 2026-10-26 |

Pattern modules worth knowing when `patterns/` fills: `avm-ptn-network-private-link-private-dns-zones`
/ `avm/ptn/network/private-link-private-dns-zones` (the privatelink zones a
`private_dns_ownership: deployment` deployment owns), `avm-ptn-alz-connectivity-hub-and-spoke-vnet`
/ `avm/ptn/network/hub-networking`.

### Resolving the current version

Never from memory, never from the table above. Three sources that need no credentials:

```powershell
# Bicep: the public registry's tag list. Highest semver wins.
(Invoke-RestMethod 'https://mcr.microsoft.com/v2/bicep/avm/res/storage/storage-account/tags/list').tags |
  Sort-Object { [version]$_ } | Select-Object -Last 1

# Terraform: the module repository's tags (the registry mirrors them).
git ls-remote --tags https://github.com/Azure/terraform-azurerm-avm-res-storage-storageaccount |
  ForEach-Object { ($_ -split '/')[-1] } | Where-Object { $_ -notmatch '\^' } | Sort-Object { [version]($_ -replace '^v') } | Select-Object -Last 1

# Either: the module's README, which is generated from the code and carries every input.
# https://raw.githubusercontent.com/Azure/terraform-azurerm-avm-res-<ns>-<type>/main/README.md
# https://raw.githubusercontent.com/Azure/bicep-registry-modules/main/avm/res/<ns>/<type>/README.md
```

Then pin **that** version: `version = "~> 0.10.0"` (patch-floating, minor-fixed, because
`0.y` minors break) in Terraform, the exact `0.33.1` in Bicep (`br/public` references take
no range). Say which version was resolved in the handover; the pin in the code is the
record, the spec never carries it.

Read the module's README **inputs section** for the version you pinned before writing the
call. Inputs are renamed between minors; an argument from memory that no longer exists is
the same failure as an invented provider attribute.

## The shared interfaces

Every AVM resource module implements the same optional interfaces, with the same names
per target. This is the mapping the resource rendering references build on — a decision
that lands in one of these lands the same way on every resource:

| Decision in the spec | Terraform input | Bicep parameter |
|---|---|---|
| `private_endpoint_subnet`, `private_endpoint_subresources` | `private_endpoints = { <key> = { subnet_resource_id, subresource_name, name } }` | `privateEndpoints: [ { service, subnetResourceId, name } ]` |
| `deployment.private_dns_records: policy` | `private_endpoints_manage_dns_zone_group = false` and no `private_dns_zone_resource_ids` | no `privateDnsZoneGroup` on the endpoint |
| `deployment.private_dns_records: deployment` | `private_dns_zone_resource_ids = [<zone id>]` per endpoint | `privateDnsZoneGroup: { privateDnsZoneGroupConfigs: [ { privateDnsZoneResourceId } ] }` |
| `diagnostic_workspace`, `diagnostic_categories`, `metrics_enabled` | `diagnostic_settings = { <key> = { workspace_resource_id, log_categories, log_groups, metric_categories } }` (sets of names; `log_groups` defaults to `["allLogs"]`, so it is set empty beside `log_categories`). **Three modules use the older object form** - `logs = [{ category }]`, `metrics = [{ category }]` - namely `web-site`, `web-serverfarm` and `insights-component`, and the storage account's per-service variants (`diagnostic_settings_blob`); read the Type block of the pinned version | `diagnosticSettings: [ { workspaceResourceId, logCategoriesAndGroups: [ { categoryGroup } ], metricCategories: [ { category } ] } ]` (nested under the service object where the resource has them, e.g. `blobServices.diagnosticSettings`) |
| `managed_identity` | `managed_identities = { system_assigned = true, user_assigned_resource_ids = [] }` | `managedIdentities: { systemAssigned: true, userAssignedResourceIds: [] }` |
| `role_assignments` | `role_assignments = { <key> = { role_definition_id_or_name, principal_id, principal_type } }` | `roleAssignments: [ { roleDefinitionIdOrName, principalId, principalType } ]` |
| `key_management: customer_managed` | `customer_managed_key = { key_vault_resource_id, key_name, user_assigned_identity = { resource_id } }` | `customerManagedKey: { keyVaultResourceId, keyName, userAssignedIdentityResourceId }` |
| `deployment.resource_lock` | `lock = { kind = "CanNotDelete" }` | `lock: { kind: 'CanNotDelete' }` |
| `context.tags` | `tags = local.tags` | `tags: tags` |
| `deployment.module_telemetry` | `enable_telemetry = true` / `false` | `enableTelemetry: true` / `false` |

**Which resources are locked.** `deployment.resource_lock` puts a `CanNotDelete` lock, in the
stages it names, on the resources whose loss cannot be undone from the spec: `storage-account`,
`cosmos-db`, `key-vault`, `backup-vault`, `recovery-services-vault`, `log-analytics-workspace`,
`service-bus`, `event-hubs`, `event-grid-namespace`, `container-registry`, `search-service`, `sql-managed-instance`, `purview-account` and `public-dns-zone` (a recreated zone has new name servers and breaks every delegation). Compute, identities, network
resources and network security groups carry none - a lock on a virtual network also blocks changing
its subnets. A lock blocks `terraform destroy` and removing the resource from the spec; the
handover says that the lock comes off first.

Map keys on the Terraform side are arbitrary and stable — use the decision's own key
(`blob`, `file`) so the resource address reads as the decision does. Role assignments take
the role **by name** in both targets (`"Storage Blob Data Contributor"`), which removes the
GUID table the authored Bicep render needed.

**Telemetry.** Every AVM module sends a deployment telemetry event to Microsoft unless
told not to; the Terraform modules do it through the `Azure/modtm` provider, the Bicep
modules through an empty nested deployment. It is a deployment decision
(`deployment.module_telemetry`, default `disabled`) and is rendered explicitly on every call
either way, so a reviewer sees it was decided.

## Provider requirements (Terraform)

An AVM Terraform module brings its own provider requirements, and the root has to satisfy
the **union** of them. Read each module's README *Requirements* before writing
`providers.tf`; today that means:

- **AzAPI-based modules** (storage account, virtual network, more every quarter) require
  `Azure/azapi ~> 2.11`, `Azure/modtm ~> 0.3`, `hashicorp/random`, and Terraform `>= 1.10`
  (the storage module at v0.10.0; `hashicorp/time` arrives transitively through
  `avm-utl-interfaces` and needs no root declaration).
  They take the resource group as `parent_id` — a resource **id**, not a name — and no
  longer need `azurerm` at all. They authenticate with Entra ID always, so
  `shared_access_key_enabled = false` costs nothing on the module side.
- **azurerm-based modules** (Log Analytics workspace) still pin `azurerm`, and the
  workspace module pins it to **4.x**. A root that needs that module cannot be on
  `azurerm ~> 5.0` — the module's constraint wins, because the module is the primary path,
  and the authored fallback code in that root follows the 4.x spelling (bool
  `public_network_access_enabled`). Check [terraform-idiom.md](terraform-idiom.md) for
  what differs between the two majors before mixing.
- **The root keeps `azurerm` for what the modules do not do**: the `data` blocks that
  reference the platform (`azurerm_subnet`, `azurerm_log_analytics_workspace`), and any
  authored fallback resource. The `naming` provider stays as before; the module takes the
  rendered name as `name`.

So a typical root declares `azurerm`, `azapi`, `modtm`, `random` and `naming`. `modtm` and
`random` are transitive: declaring them in the root is what lets `terraform init` resolve
one version for the whole configuration, and what the lock file pins.

## Rendering a call

The decision set of a resource becomes one module block. Three rules carry over from the
authored idiom and one is new:

1. **Every decision is written, even at the module default.** The module default is not
   the guardrail's, and a reviewer reads the call, not the module.
2. **Context values stay variables; the name comes from the naming provider / vars.**
   `name = data.naming_name.storage_account.name`, `location = var.location`,
   `parent_id = data.azurerm_resource_group.this.id` (AzAPI module) or
   `resource_group_name = var.resource_group_name` (azurerm module).
3. **Wiring stays in the root.** The module's own interfaces (its private endpoints, its
   role assignments) are inputs to that module; a role assignment *between* two modules is
   root-level wiring as before.
4. **New: comment the decision key on inputs whose name does not say it.** A bool
   `public_network_access_enabled = false` under a spec that says
   `public_network_access: disabled` carries `# decision: storage-account.networking.public_network_access`
   on the line above, the same marker the tests use. A reviewer maps code to decision
   without the question set open.

Each resource's `terraform.md` and `bicep.md` opens with the decision → module input table
and the rendered call for the current module version. The authored rendering follows it,
for the `implementation: authored` case and for reading what the module does inside.

## Gaps: what the module does not carry

A module swallows a decision in one of three ways. Each has a rule:

| The module… | Rule |
|---|---|
| **Has no input for it** (e.g. a question the module's authors did not think worth exposing) | Name it in the handover as *not carried by the module*, keep the decision in the spec, and if it matters for the deployment either add the attribute through the module's escape hatch (`_target_overrides`, with the module's `azapi` `ignore_body_changes` / `resource_types` where it has one) or render that resource authored. Never silently drop it |
| **Fixes it the other way** (a default the module does not let you change) | A finding for the question set, not for the render: either the guardrail is wrong or the module is, and the spec records the value actually deployed with `source: forced`, `forced_by: <module>` |
| **Exposes it under a different shape** (bool for a string, days-without-enabled, a nested object) | Normal rendering. The resource reference maps it, the test asserts the spec's value through the module's shape |

The check is mechanical: walk the resource's spec decisions against the module's input
list, once per module version. The resource references do this for the version they
document; a newer version is re-walked, not assumed.

## Tests with a module in the middle

The contract from [terraform-idiom.md](terraform-idiom.md#tests) holds — one assert per
spec decision, named by its key path, or a `# not-testable:` marker with a reason — but
the root no longer owns the resource, so the assert target moves. Settled by the first
AVM render (a storage account on a referenced platform, storage module v0.10.0, 2026-10-18):

- **Mock `azapi` and `modtm` as the platform is mocked.** `mock_provider "azapi" {}` and
  `mock_provider "modtm" {}` beside the `azurerm` mock; the naming provider stays real.
  The root's `data "azurerm_resource_group"` (the module's `parent_id`) needs a mocked
  id that parses, like the other platform data sources.
- **Assert through the module's `resource` output.** It is the `azapi_resource` the
  module creates, and its `body` is what the root passed in, so it is known at plan
  time. What a plan observes there: `body.sku.name`, every `body.properties.*` the
  account carries (`publicNetworkAccess`, `networkAcls.defaultAction` and `.bypass`,
  `allowSharedKeyAccess`, `minimumTlsVersion`, `supportsHttpsTrafficOnly`,
  `allowBlobPublicAccess`, `encryption.requireInfrastructureEncryption` and
  `.keySource`, `isSftpEnabled`, `accessTier`, `immutableStorageWithVersioning`),
  `identity[0].type`, `name`, `parent_id`, and `create_headers` (non-null only with
  telemetry on). The `private_endpoints` output carries each endpoint's `name` and a
  `private_dns_zone_group_id` that is `null` — known, not unknown — when the module
  does not manage the zone group.
- **The `resource` output is `sensitive`.** A condition on it evaluates normally, but a
  failing assert prints `(sensitive value)` instead of the actual value, and an
  `error_message` cannot interpolate it. So the error message states the expected
  value in words, and a failure is diagnosed by reading the call, not the diff.
- **What the root cannot observe is marked, not skipped.** The module creates the blob
  service, the diagnostic settings, the role assignments and the private endpoint's
  body in child modules, and nothing of their bodies reaches an output. Those decisions
  carry `# not-testable: <key> - set through the module's <input>; the module's own
  tests cover the mapping`. For the storage account that is nine of twenty-four
  decisions: the five blob-service ones, the three diagnostic ones, and
  `role_assignments`; plus `private_endpoint_subnet`, whose id goes into the endpoint
  child module. That sentence is the honest state: the module's test suite is part of
  the verification story, and the marker says which decisions lean on it.
- **The module's own tests are not re-run here.** They ran before the version was
  published. What the render tests prove is that *this* root passes *these* decisions —
  which is the part a module cannot test for you.

**What twelve more modules showed** (a chatbot render, 2026-10-23) - the contract holds, the
reachable surface varies by module, and one module cannot be tested at all:

- **A module's `resource` output is one of three things.** The `azapi_resource` itself (storage,
  virtual network, App Service site, function app): assert on `resource.body.properties.*`. The
  attributes of the former `azurerm` resource, echoed from the inputs (Log Analytics, Search,
  Application Insights, Foundry, identity): assert on `resource.<attribute>`, for Foundry under
  the `azurerm` spelling (`public_network_access`, `local_authentication_enabled`). Or nothing:
  Key Vault, Container Registry and the Container App module expose no attribute at all, and the
  plan modules only `name` and `resource_id`, so their decisions are `# not-testable:` and the
  call is the review. Cosmos DB exposes many attributes as outputs of their own.
- **A list is compared as JSON.** A `list(string)` output and a list literal are different types
  in HCL (`list` against `tuple`), so `x == ["a"]` is false for equal values: compare
  `jsonencode(x) == jsonencode([...])`.
- **A module with an ephemeral resource cannot be planned under mock providers.**
  `avm-res-app-managedenvironment` declares one in every version, even at `count = 0`, and
  `override_module` does not help: the root cannot be tested at all while the module is in it.
  The render uses an authored `azapi_resource` for it and records the departure in the spec
  (`_target_overrides`).
- **Some modules need a mocked `azapi` data source.** The Flex plan module reads the regions
  that advertise zone-redundant Flex Consumption (`azapi_resource_action`), the Application
  Insights module the subscription's resource id (`azapi_client_config`): `mock_data` with a
  value of the right shape, or the plan fails before any assert.
- **The unreachable share is large and honest.** 79 of 284 decisions of that chatbot render are
  asserted, 205 are marked with a reason - mostly private endpoints, role assignments, diagnostic
  settings and sub-resources the modules build in children. Say it in the handover.

`check_render_coverage.py` accepts either an assert or a marker per decision, never both.

Bicep asserts on the compiled ARM ([bicep-idiom.md](bicep-idiom.md#tests)): a module call
compiles to a nested deployment whose `properties.parameters.<param>.value` is the
decision, a loop to a `copy` whose expression text names the literal. `bicep build`
resolves the module from `mcr.microsoft.com`, so the tests need that network access and
nothing else. Settled by a three-module Bicep render: 41 of 43 decisions across three modules
are observable in the compiled template; the two that are not are a deletion-time
parameter and a spec-only record.

## When not to use a module

- **The repository already renders the resource authored** and the user did not ask to
  migrate. Matching the repository beats the default (iac-rendering, *Order of work* 1);
  moving a deployed resource into a module is a state migration (`moved` blocks in
  Terraform, a redeploy with the same names in Bicep) and is its own task.
- **The user named a module that is not AVM.** `implementation: reuse` with the
  coordinate in `_target_overrides`, as before.
- **A pattern skill owns the composition and an AVM pattern module overlaps it.** Prefer
  the AVM pattern module when it covers the pattern; prefer the resource modules under the
  skill's own wiring when it does not. Never both for one part.
