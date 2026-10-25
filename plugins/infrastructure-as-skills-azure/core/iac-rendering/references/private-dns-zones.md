# Private DNS zones per private endpoint

`wiring.private_dns_zones` in the spec lists the privatelink zones a deployment either creates
(`deployment.private_dns_ownership: deployment`) or references (`platform`). Which zone belongs to
which private endpoint is fixed by Azure and is the same for every deployment, so it is a table
here and not a decision: **every resource that gets a private endpoint adds its zone(s) to the
list**, and a resource added after the list was written adds its own. A zone missing from the
list is the usual reason a private endpoint is created and nothing resolves to it.

Source: Microsoft Learn, *Azure Private Endpoint private DNS zone values* (looked up 2026-10-25).
The names below are the public cloud's. The sovereign clouds (US Government, China) use other
suffixes, and a few zones carry a region or an account-specific part: look the row up again in
that page for the cloud and region in use rather than editing a zone by hand.

| Question set | Private endpoint sub-resource | Zone(s) | Notes |
|---|---|---|---|
| `storage-account` | `blob` | `privatelink.blob.core.windows.net` | One endpoint and one zone per sub-resource used; `*_secondary` for the read-access geo copy |
| | `file` | `privatelink.file.core.windows.net` | |
| | `queue` | `privatelink.queue.core.windows.net` | |
| | `table` | `privatelink.table.core.windows.net` | |
| | `dfs` | `privatelink.dfs.core.windows.net` | Data Lake Gen2 |
| | `web` | `privatelink.web.core.windows.net` | Static website |
| `key-vault` | `vault` | `privatelink.vaultcore.azure.net` | |
| `cosmos-db` | `Sql` | `privatelink.documents.azure.com` | API for NoSQL; the analytical store and the dedicated gateway have zones of their own (`privatelink.analytics.cosmos.azure.com`, `privatelink.sqlx.cosmos.azure.com`) |
| `foundry` | `account` | `privatelink.cognitiveservices.azure.com`, `privatelink.openai.azure.com`, `privatelink.services.ai.azure.com` | All three, for an account that serves Foundry and Azure OpenAI |
| `search-service` | `searchService` | `privatelink.search.windows.net` | |
| `container-registry` | `registry` | `privatelink.azurecr.io`, `{region}.data.privatelink.azurecr.io` | The second zone is the data endpoint, one per replicated region |
| `app-service`, `function-app` | `sites` | `privatelink.azurewebsites.net`, `scm.privatelink.azurewebsites.net` | The second one is the Kudu/SCM site; **each app on a shared plan has its own endpoint but the zones are shared** |
| `container-apps` | `managedEnvironments` | `privatelink.{region}.azurecontainerapps.io` | Per region |
| `service-bus` | `namespace` | `privatelink.servicebus.windows.net` | Premium only |
| `event-hubs` | `namespace` | `privatelink.servicebus.windows.net` | The same zone as Service Bus; one zone serves both |
| `event-grid-topic` | `topic` | `privatelink.eventgrid.azure.net` | |
| `api-management` | `Gateway` | `privatelink.azure-api.net` | Tiers with private endpoint support. An `internal` injected instance has no endpoint: it needs an `azure-api.net` zone (or its custom domain's) with records for the gateway hostnames, created by the pattern |
| `recovery-services-vault` | `AzureBackup` | `privatelink.{regionCode}.backup.windowsazure.com`, `privatelink.blob.core.windows.net`, `privatelink.queue.core.windows.net` | The backup service reaches the data through the blob and queue zones as well |
| `backup-vault` | - | - | The Backup vault takes no private endpoint in this plugin |
| `application-insights`, `log-analytics-workspace` | `azuremonitor` (the Azure Monitor Private Link Scope, not the component) | `privatelink.monitor.azure.com`, `privatelink.oms.opinsights.azure.com`, `privatelink.ods.opinsights.azure.com`, `privatelink.agentsvc.azure-automation.net`, `privatelink.blob.core.windows.net` | The scope belongs to the platform; see the workspace set |
| `application-gateway`, `front-door`, `virtual-network`, `network-security-group`, `user-assigned-identity` | - | - | No private endpoint of their own |

## How a zone ends up in the spec

1. The interview resolves `private_dns_ownership` and `private_dns_records`
   ([deployment.yaml](../../iac-authoring/questions/deployment.yaml)).
2. For `private_dns_ownership: deployment` the pattern or the render adds one zone to
   `wiring.private_dns_zones` per row above that a resource of the spec uses, and creates it
   once, linked to the network. For `platform` the same list names the zones the platform must
   already have, an `open:` entry for each the platform cannot confirm.
3. `private_dns_records` decides whether the endpoint attaches the zone itself (`deployment`) or
   leaves the record to the platform's policy (`policy`) - see
   [avm.md](avm.md#the-shared-interfaces).

The zone is per kind of endpoint, the endpoint is per resource. A second App Service on the same
plan gets a private endpoint of its own and needs no new zone: `privatelink.azurewebsites.net` is
already in the list, and the new endpoint writes its record into it. The mistake to avoid is the
reverse, a list built from the first app only that lacks the zone when the first app has no
endpoint of its own.
