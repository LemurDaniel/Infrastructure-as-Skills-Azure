# Decisions for "chatbot"

What will be built, decided from your answers and the rules behind the defaults. Every line is one decision; the key in the appendix is where an engineer finds it in the specification.

As of 2026-10-23. Specification: `infra-spec.yaml`.

## The system

- The system is deployed in these stages: live operation.
- Everything runs in the Azure region westeurope.
- "chatbot" is the name every part of the system carries.
- Each stage lives in its own subscription, so the stages cannot touch each other's resources, budgets or permissions.

## Resource groups

A resource group is the unit that is deleted, permitted and costed as a whole. Each group is either created with the system or already exists and is only used.

| Group | State | Name | Contains |
|---|---|---|---|
| main | created with the system | named by the naming convention | Azure Key Vault, Azure user-assigned managed identity (connector), Azure user-assigned managed identity (runner), Azure user-assigned managed identity (web) |
| network | exists, only used | `rg-spoke-chatbot-prod-we` | Azure Network Security Group (containerapps), Azure Network Security Group (endpoints), Azure Network Security Group (integration), Azure Virtual Network |
| data | created with the system | named by the naming convention | Azure Cosmos DB account (API for NoSQL), Azure Storage Account (uploads) |
| application | created with the system | named by the naming convention | Azure AI Foundry (AI Services account with projects and model deployments), Azure AI Search service, Azure App Service (web app on an App Service plan) (mcp), Azure App Service (web app on an App Service plan) (web), Azure Container Apps (environment and one container app), Azure Container Registry, Azure Functions (function app on Flex Consumption or Elastic Premium), Azure Storage Account (host) |
| monitoring | created with the system | named by the naming convention | Azure Application Insights (workspace-based), Azure Log Analytics Workspace |

## What follows from your answers

- **These areas get a resource group of their own: network, data, application, monitoring. Everything else shares the main group.** _(from your description)_
- **A day's outage would be disruptive.** _(not said, so the usual answer applies)_
  - therefore, Azure Storage Account (uploads): The data is kept in three datacenters of the region, so one can fail.
  - therefore, Azure Storage Account (host): The data is kept in three datacenters of the region, so one can fail.
  - therefore, Azure Cosmos DB account (API for NoSQL): The data do survive the loss of one datacenter of the region.
  - therefore, Azure AI Search service: 2 copies of the index answer queries.
  - therefore, Azure Container Registry: The registry does survive the loss of one datacenter of the region.
  - therefore, Azure Container Apps (environment and one container app): The environment does survive the loss of one datacenter of the region.
  - therefore, Azure Container Apps (environment and one container app): At least 2 copies of the app are always running.
  - therefore, Azure Functions (function app on Flex Consumption or Elastic Premium): The function app does survive the loss of one datacenter of the region.
  - therefore, Azure Functions (function app on Flex Consumption or Elastic Premium): 1 instance(s) are kept warm so the first call does not wait.
  - therefore, Azure App Service (web app on an App Service plan) (web): The app does survive the loss of one datacenter of the region.
  - therefore, Azure App Service (web app on an App Service plan) (web): Copies of the app running at the same time: 2.
  - therefore, Azure App Service (web app on an App Service plan) (mcp): The app does survive the loss of one datacenter of the region.
  - therefore, Azure App Service (web app on an App Service plan) (mcp): Copies of the app running at the same time: 2.
- **After a mistaken delete you must be able to go back a week.** _(not said, so the usual answer applies)_
  - therefore, Azure Storage Account (uploads): Deleted files can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account (uploads): Deleted folders can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account (uploads): Earlier versions of overwritten files are kept.
  - therefore, Azure Storage Account (host): Deleted files can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account (host): Deleted folders can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account (host): Earlier versions of overwritten files are kept.
  - therefore, Azure Cosmos DB account (API for NoSQL): Backups allow going back to any second of the last seven days.
- **The data is worked with all the time.** _(not said, so the usual answer applies)_
  - therefore, Azure Storage Account (uploads): Stored in the standard - cheap to read, for data in use class.
  - therefore, Azure Storage Account (host): Stored in the standard - cheap to read, for data in use class.
- **Against deliberate destruction the data is protected only inside the system itself - whoever can delete the system can delete the copies.** _(not said, so the usual answer applies)_
- **The data is stored and processed only inside the region's economic area, for example the EU.** _(from your description)_
  - therefore, Azure AI Foundry (AI Services account with projects and model deployments): Requests to the models are processed anywhere inside the same data zone (for example the EU).
- **The code is built from Microsoft's verified, tested building blocks (Azure Verified Modules).** _(not said, so the usual answer applies)_
- **Access is private only - nothing is reachable from the internet.** _(from your description)_
- **Rules to comply with: Datenverarbeitung nur in der EU.** _(from your description)_
- **Logs are kept for 30 days.** _(from your description)_

## Set by the rules

Nothing here was asked; each follows a rule or one of the answers above. Say so if one is wrong.

### For the whole system

- The main resource group is created together with the system.
- The network resource group already exists and is only used.
- The data resource group is created together with the system.
- The application resource group is created together with the system.
- The monitoring resource group is created together with the system.
- Created resource groups carry a delete lock in production.
- Usage telemetry to Microsoft is on: a count per deployment, none of your data.
- The system lands in the internal part of the company platform, connected to the company network. _(please confirm)_
- Passwords and access keys are switched off; access goes through company accounts, so every action is attributable. _(please confirm)_
- Encryption keys are protected in software - the standard, sufficient unless a mandate names hardware.
- Encryption keys are managed by Azure - encrypted, rotated, no effort on your side. _(please confirm)_
- The network is built by this deployment.
- The new network uses the address range 10.20.0.0/16.
- Private connections get their own subnet, 10.20.0.0/27.
- Name resolution for private connections is handled by the company platform.
- The name entries for private connections are written by a platform rule, automatically.
- Logs go to a workspace this deployment creates and pays for.
- Logs are collected in log-analytics-workspace. — because: Logs go to a workspace this deployment creates and pays for.
- Daily log intake cap: -1 GB (-1: no cap). _(please confirm)_

### Security

The security baseline of every part in one place. None of it was asked and it is the same in every stage; say so if one does not fit.

- **Azure Virtual Network**
  - A paid DDoS protection plan is not used; Azure's basic protection applies either way. _(please confirm)_
  - Subnets that will get a security group: snet-endpoints, snet-web, snet-mcp, snet-func, snet-aca.
- **Azure Application Insights (workspace-based)**
  - Access rights on the component granted to: user-assigned-identity__connector (Monitoring Metrics Publisher).
  - Sending telemetry with only a key is switched off; applications sign in with company identities. _(please confirm)_
- **Azure Key Vault**
  - Access rights on the vault granted to: user-assigned-identity__web (Key Vault Secrets User), user-assigned-identity__connector (Key Vault Secrets User).
  - Platform services allowed to read from the vault: none (empty: none).
  - Empty slots are created for the secrets entra-client-secret; their values are entered afterwards by hand or by the workload.
- **Azure Storage Account**
  - The storage has its own identity for reaching other services.
  - Access rights granted to: user-assigned-identity__web (Storage Blob Data Contributor), search-service (Storage Blob Data Reader). (uploads)
  - Access with a shared key is not possible; access goes through company accounts. _(please confirm)_
  - Connections must use at least TLS 1.2 encryption.
  - Unencrypted connections are refused.
  - Making individual folders publicly readable is not possible.
  - A second encryption layer below the service is on.
  - Encryption keys are managed by Azure - encrypted, rotated, no effort on your side.
  - File transfer via SFTP is off.
  - Access rights granted to: user-assigned-identity__connector (Storage Blob Data Owner), user-assigned-identity__connector (Storage Table Data Contributor), user-assigned-identity__connector (Storage Queue Data Contributor). (host)
- **Azure Cosmos DB account (API for NoSQL)**
  - The account has no identity of its own.
  - Access to the data itself granted to: user-assigned-identity__web (Cosmos DB Built-in Data Contributor).
  - Management rights on the account granted to: none.
  - Signing in with account keys is switched off; access goes through company accounts. _(please confirm)_
  - Creating or changing databases, containers and throughput with account keys is switched off.
  - Encryption keys are managed by Azure - encrypted, rotated, no effort on your side. _(please confirm)_
- **Azure AI Foundry (AI Services account with projects and model deployments)**
  - The account has its own identity.
  - Access rights on the account granted to: user-assigned-identity__web (Cognitive Services OpenAI User), user-assigned-identity__connector (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
  - Signing in with account keys is switched off; access goes through company accounts. _(please confirm)_
  - Encryption keys are managed by Azure - encrypted, rotated, no effort on your side. _(please confirm)_
- **Azure AI Search service**
  - The search service has its own identity.
  - Access rights on the search service granted to: user-assigned-identity__web (Search Index Data Reader), user-assigned-identity__connector (Search Index Data Contributor).
  - Signing in with API keys is switched off; access goes through company accounts. _(please confirm)_
  - Encryption keys are managed by Azure - encrypted, rotated, no effort on your side. _(please confirm)_
- **Azure Container Registry**
  - The registry has no identity of its own.
  - Access rights on the registry granted to: user-assigned-identity__runner (AcrPull).
  - The shared admin account is switched off; access goes through company accounts. _(please confirm)_
  - Pulling images without signing in is not allowed.
  - Encryption keys are managed by Azure - encrypted, rotated, no effort on your side. _(please confirm)_
- **Azure Container Apps (environment and one container app)**
  - The app has a shared, separately managed identity for reaching other services.
  - It uses the identity user-assigned-identity__runner.
  - The app reads the secrets none from the key vault.
  - Management rights on the app granted to: none.
- **Azure Functions (function app on Flex Consumption or Elastic Premium)**
  - The function app has a shared, separately managed identity for reaching other services.
  - It uses the identity user-assigned-identity__connector.
  - Management rights on the function app granted to: none.
  - Unencrypted connections are redirected to the encrypted address.
  - Connections must use at least TLS 1.2 encryption.
  - Deploying with a user name and password is not possible; deployments run through company accounts. _(please confirm)_
  - Its application telemetry goes to application-insights (empty: none).
- **Azure App Service (web app on an App Service plan)**
  - The app has a shared, separately managed identity for reaching other services.
  - It uses the identities user-assigned-identity__web.
  - Unencrypted connections are redirected to the encrypted address.
  - Connections must use at least TLS 1.2 encryption.
  - File upload by FTP is switched off.
  - Deploying with a user name and password is not possible; deployments run through company accounts. _(please confirm)_

### Azure Virtual Network

- The network uses the address range 10.20.0.0/16.
- Subnets: snet-endpoints (10.20.0.0/27), snet-web (10.20.0.64/26), snet-mcp (10.20.0.128/26), snet-func (10.20.0.192/26), snet-aca (10.20.1.0/27).
- Private connections get the subnet 10.20.0.0/27.
- Custom name servers: none (none: Azure's own).
- Network rules apply to private connections in their subnet.
- Shortcuts to Azure services from the subnets: none.
- Subnets handed to a service: snet-web (Microsoft.Web/serverFarms), snet-mcp (Microsoft.Web/serverFarms), snet-func (Microsoft.App/environments), snet-aca (Microsoft.App/environments). — because: `resources.app-service__web.networking.integration_subnet`
- Network logs go to log-analytics-workspace.
- A record of allowed and denied traffic is not kept. _(please confirm)_

### Azure Network Security Group (endpoints)

- The group guards a subnet for private connections to Azure services.
- Inbound traffic that no rule allows is refused, including traffic from other machines in the same network.
- Outbound traffic to the internet that no rule allows is refused; what must go out goes through the company firewall. — because: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Traffic allowed explicitly: none.
- Its logs go to log-analytics-workspace.
- Logged: which rule was applied to which machine, how often each rule matched.

### Azure Network Security Group (integration)

- The group guards a subnet for the outgoing traffic of web and function apps.
- Inbound traffic that no rule allows is refused, including traffic from other machines in the same network.
- Outbound traffic to the internet that no rule allows is left to Azure's built-in rules, which let it out.
- Traffic allowed explicitly: none.
- Its logs go to log-analytics-workspace.
- Logged: which rule was applied to which machine, how often each rule matched.

### Azure Network Security Group (containerapps)

- The group guards a subnet for the infrastructure of a container environment.
- Inbound traffic that no rule allows is refused, including traffic from other machines in the same network.
- Outbound traffic to the internet that no rule allows is left to Azure's built-in rules, which let it out.
- Traffic allowed explicitly: none.
- Its logs go to log-analytics-workspace.
- Logged: which rule was applied to which machine, how often each rule matched.

### Azure Log Analytics Workspace

- Logs are kept for 30 days.
- Daily log intake cap: -1 GB (-1: no cap). _(please confirm)_
- Billed per gigabyte, pay as you go.
- The log workspace is reachable from the internet, with company accounts and encryption - there is no private link scope to go through. _(please confirm)_
- Sending logs with the workspace key is not possible - agents use company identities.
- Who may read logs is decided by the workspace's own permissions.
- A deleted workspace can be recovered for 14 days.
- Long-term archiving to cheap storage is off.

### Azure Application Insights (workspace-based)

- Its telemetry is stored in log-analytics-workspace.
- The component is set up for a web application or a service.
- 100 percent of the telemetry is kept.
- Daily telemetry cap for this component: 0 GB (0: no cap). _(please confirm)_
- Visitors' IP addresses are masked and not stored.
- The component is reachable only through the private monitoring connection, for sending and for reading. _(please confirm)_

### Azure Key Vault

- The vault is the standard, keys protected in software tier.
- A deleted vault or secret cannot be wiped, not even by an administrator before its retention ends.
- Deleted vault contents can be restored for 90 days.
- Access to the vault's contents is controlled by role assignments, like everything else in Azure.
- The vault is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the vault's firewall.
- Encryption keys are managed by Azure - the vault holds none for encryption.
- Its logs go to log-analytics-workspace.
- Logged: every read, write and failed access to the vault, how policies judged the vault.
- Usage and performance figures are collected.

### Azure user-assigned managed identity (web)

- This identity exists for the web app and the MCP server, to reach models, search, data and secrets.
- External systems trusted to act as this identity: none (empty: none).
- The identity can be used from resources in any region.
- Rights on the identity itself granted to: none.

### Azure user-assigned managed identity (connector)

- This identity exists for the document connector function, to index documents and keep its own state.
- External systems trusted to act as this identity: none (empty: none).
- The identity can be used from resources in any region.
- Rights on the identity itself granted to: none.

### Azure user-assigned managed identity (runner)

- This identity exists for the code interpreter container app, to pull its image.
- External systems trusted to act as this identity: none (empty: none).
- The identity can be used from resources in any region.
- Rights on the identity itself granted to: none.

### Azure Storage Account (uploads)

- The storage is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Private connections exist for: files (blob).
- Azure's own services (backup, monitoring) may reach the storage past the firewall.
- A log of every change is not kept.
- The whole storage can be rewound 0 days (0: not at all).
- Deletion protection by law or policy: none.
- Its logs go to log-analytics-workspace.
- Logged: who accessed what.
- Usage and performance figures are collected.

### Azure Storage Account (host)

- The storage is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Private connections exist for: files (blob), queues, tables. — because: `resources.function-app.storage.host_storage_account`
- Azure's own services (backup, monitoring) may reach the storage past the firewall.
- A log of every change is not kept.
- The whole storage can be rewound 0 days (0: not at all).
- Deletion protection by law or policy: none.
- Its logs go to log-analytics-workspace.
- Logged: who accessed what.
- Usage and performance figures are collected.

### Azure Cosmos DB account (API for NoSQL)

- Capacity is reserved up front and billed by the hour, with a guaranteed rate. _(please confirm)_
- Throughput follows the load between a tenth of the ceiling and the ceiling.
- Throughput is capped at 1000 request units per second per container.
- The account as a whole may use at most -1 request units per second (-1: no limit).
- The monthly free allowance of throughput and storage is not used.
- The data is also kept in none (empty: only in the main region).
- If the main region fails, the account switches to a replica region on its own.
- A read sees its own writes at once and, for others, a slightly older state.
- The account is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the account's firewall.
- A column store for analytics beside the data is not kept.
- The account holds the databases and containers chatbot containers [{'name': 'conversations', 'partition_key_paths': ['/userId']}].
- Its logs go to log-analytics-workspace.
- Logged: every change to the account, its databases and containers, every request to the data, with its cost and result.
- Usage and performance figures are collected.

### Azure AI Foundry (AI Services account with projects and model deployments)

- The account is an AI Foundry resource, which also offers projects, agents and the other AI services.
- The account uses the pricing tier S0, the standard paid tier - the only one that has projects and private endpoints in production.
- The account holds Foundry projects, as containers for access, data and cost.
- The account holds the projects chatbot.
- The account serves the models chat format OpenAI, model gpt-4.1, version 2025-04-14, embeddings format OpenAI, model text-embedding-3-large, version 1.
- Each model may process up to 10 thousand tokens per minute.
- When the model version expires, it moves to the new default version on that day.
- Prompts and answers are checked by the content filter Microsoft.DefaultV2.
- The account is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- The account may call out only to addresses that are explicitly allowed.
- Its logs go to log-analytics-workspace.
- Logged: changes to the account and who made them, every request to the models, with its caller, size and result (not the text), the tokens each call used.
- Usage and performance figures are collected.

### Azure AI Search service

- The search service is the standard, the normal production tier tier. _(please confirm)_
- The index data is spread over 1 partition(s).
- Re-ranking of results by meaning is on, within a small free monthly allowance.
- The search service is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the search service's firewall.
- Its logs go to log-analytics-workspace.
- Logged: every query and every change to indexes and indexers.
- Usage and performance figures are collected.

### Azure Container Registry

- The registry is the premium, which alone can be closed off with a private connection and spread over several regions tier. — because: Access is private only - nothing is reachable from the internet.
- The images are also kept in none (empty: only in the main region).
- Untagged images are deleted after 7 days.
- The registry is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the registry's firewall.
- Copying images out of the registry to elsewhere is blocked.
- Its logs go to log-analytics-workspace.
- Logged: every push, pull and delete of an image, every sign-in to the registry.
- Usage and performance figures are collected.

### Azure Container Apps (environment and one container app)

- The app runs on shared capacity that is billed per use and scales to nothing.
- The environment is reachable only from inside the company network, through an internal load balancer. _(please confirm)_
- The environment's infrastructure lives in subnet snet-aca. — because: The network is built by this deployment.
- The environment is closed to all public traffic. _(please confirm)_
- Traffic between the apps inside the environment is encrypted.
- The app runs the container image container-registry/code-runner:1.0.0.
- Each copy of the app gets half a core and one gigabyte.
- The app may scale out to at most 10 copies.
- Only the newest version of the app runs; a new one replaces it.
- The app is callable only by other apps in its environment. _(please confirm)_
- The app listens on port 8080.
- Unencrypted connections to the app are redirected to the encrypted address.
- Its logs go to log-analytics-workspace.
- Logged: what the app writes to its console, the platform's own messages about the app and its revisions.
- Usage and performance figures are collected.

### Azure Functions (function app on Flex Consumption or Elastic Premium)

- The function app runs on capacity that scales from zero and is billed by use, with a private network and optional warm instances.
- The function app is written for Python.
- Runtime version 3.12.
- The function app may scale out to at most 20 instances.
- Each instance gets 2048 MB of memory.
- The function app keeps its own state in the storage account storage-account__host.
- The function app signs in to its storage with its managed identity, with no secret stored. _(please confirm)_
- The deployed code is kept in the container app-package.
- The function app is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- The function app's own outgoing traffic goes through the company network, so it can reach private services.
- Outgoing traffic leaves through the subnet snet-func. — because: The network is built by this deployment.
- Outgoing traffic is routed entirely through the company network, including to the internet.
- Its logs go to log-analytics-workspace.
- Logged: what the functions write to their log, who signed in to deploy or manage the app.
- Usage and performance figures are collected.

### Azure App Service (web app on an App Service plan) (web)

- The app runs on Linux.
- The hosting plan is size P1v3, premium, the normal production size. _(please confirm)_
- The app is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- The app's own outgoing traffic goes through the company network, so it can reach private services.
- Outgoing traffic leaves through the subnet snet-web. — because: The network is built by this deployment.
- Outgoing traffic is routed entirely through the company network, including to the internet.
- The app is written for Python.
- Runtime version 3.12.
- The app stays loaded and answers the first request at once when there is no traffic.
- The platform checks the app's health at the path  (empty: not checked).
- HTTP/2 is on.
- Its logs go to log-analytics-workspace.
- Logged: every web request, the app's own log messages, who signed in to deploy or manage the app, changes to the access restrictions, the platform's own messages about the app.
- Usage and performance figures are collected.

### Azure App Service (web app on an App Service plan) (mcp)

- The app runs on Linux.
- The hosting plan is size P1v3, premium, the normal production size. _(please confirm)_
- The app is not reachable from the internet at all. _(please confirm)_
- Its private connection lands in subnet snet-endpoints. — because: The network is built by this deployment.
- The app's own outgoing traffic goes through the company network, so it can reach private services.
- Outgoing traffic leaves through the subnet snet-mcp. — because: The network is built by this deployment.
- Outgoing traffic is routed entirely through the company network, including to the internet.
- The app is written for Node.js.
- Runtime version 22-lts.
- The app stays loaded and answers the first request at once when there is no traffic.
- The platform checks the app's health at the path  (empty: not checked).
- HTTP/2 is on.
- Its logs go to log-analytics-workspace.
- Logged: every web request, the app's own log messages, who signed in to deploy or manage the app, changes to the access restrictions, the platform's own messages about the app.
- Usage and performance figures are collected.

## Decided differently by you

- Azure Storage Account (host): `"application"` _(reason: The Function App's own state lives and is rebuilt with the application, not with the data group.)_

## Still open

Nothing can be deployed until these are answered.

- Which private monitoring connection should the component belong to? _(needed from: platform team)_ — blocks: apply
- Where does the code live, and which system deploys it? The request names none, so no pipeline is rendered. _(needed from: workload owner)_ — blocks: apply
- Which tag set does the organisation apply? Nothing in the request, no repository to read it from. _(needed from: workload owner)_ — blocks: apply
- The Entra app registration and its client secret. A directory object, not an Azure resource - the identity team creates it; the secret goes into the key vault placeholder `entra-client-secret`. _(needed from: identity team)_ — blocks: apply
- The search service indexes the uploads over a shared private link, approved on the storage account. Not rendered: wiring between two resources that no question set owns. _(needed from: workload owner)_ — blocks: apply
- Is there quota for gpt-4.1 and text-embedding-3-large as DataZoneStandard in West Europe, for 10,000 tokens per minute each? Not checked; a deployment beyond the quota fails at apply. _(needed from: workload owner)_ — blocks: apply
- Is code-runner:1.0.0 pushed to the registry? The first revision pulls it while it is created, so the registry has to hold it before the app does. _(needed from: workload owner)_ — blocks: apply

## Appendix: every decision

| Key | Value | Source |
|---|---|---|
| `deployment.stage_isolation` | subscription | rule |
| `deployment.non_production_savings` | enabled | rule |
| `deployment.naming_convention` | default | rule |
| `deployment.resource_group_split` | ["network", "data", "application", "observability"] | your description |
| `deployment.resource_group_mode_main` | create | your description |
| `deployment.resource_group_mode_network` | existing | your description |
| `deployment.resource_group_mode_data` | create | your description |
| `deployment.resource_group_mode_application` | create | your description |
| `deployment.resource_group_mode_observability` | create | your answer |
| `deployment.resource_group_lock` | production | rule |
| `deployment.outage_impact` | disruptive | rule |
| `deployment.data_loss_tolerance` | one_week | rule |
| `deployment.data_access_pattern` | active | rule |
| `deployment.backup_isolation` | operational | rule |
| `deployment.data_residency` | data_zone | your description |
| `deployment.module_source` | avm | rule |
| `deployment.module_telemetry` | enabled | rule |
| `deployment.landing_zone` | corp | your description |
| `deployment.network_exposure` | private | your description |
| `deployment.local_auth` | disabled | rule |
| `deployment.mandates` | ["Datenverarbeitung nur in der EU"] | your description |
| `deployment.key_protection` | software | rule |
| `deployment.key_management` | platform_managed | rule |
| `deployment.network_ownership` | create | your description |
| `deployment.address_space` | {"production": "10.20.0.0/16"} | your description |
| `deployment.private_endpoint_subnet_prefix` | {"production": "10.20.0.0/27"} | your description |
| `deployment.private_dns_ownership` | platform | rule |
| `deployment.private_dns_records` | policy | rule |
| `deployment.observability_ownership` | create | your description |
| `deployment.diagnostics_destination` | {"production": "log-analytics-workspace"} | forced |
| `deployment.log_retention_days` | 30 | your description |
| `deployment.daily_quota_gb` | -1 | rule |
| `virtual-network.addressing.address_space` | {"production": "10.20.0.0/16"} | inherited |
| `virtual-network.addressing.subnets` | {"production": [{"name": "snet-endpoints", "prefix": "10.20.0.0/27"}, {"name": "snet-web", "prefix": "10.20.0.64/26"}, {"name": "snet-mcp", "prefix": "10.20.0.128/26"}, {"name": "snet-func", "prefix": "10.20.0.192/26"}, {"name": "snet-aca", "prefix": "10.20.1.0/27"}]} | your description |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | {"production": "10.20.0.0/27"} | inherited |
| `virtual-network.addressing.dns_servers` | {"production": []} | rule |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | rule |
| `virtual-network.subnet_policy.service_endpoints` | [] | rule |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "snet-web", "service": "Microsoft.Web/serverFarms"}, {"subnet": "snet-mcp", "service": "Microsoft.Web/serverFarms"}, {"subnet": "snet-func", "service": "Microsoft.App/environments"}, {"subnet": "snet-aca", "service": "Microsoft.App/environments"}] | forced |
| `virtual-network.security.ddos_protection` | false | rule |
| `virtual-network.security.subnets_expecting_nsg` | {"production": ["snet-endpoints", "snet-web", "snet-mcp", "snet-func", "snet-aca"]} | your description |
| `virtual-network.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `virtual-network.observability.flow_logs_enabled` | false | rule |
| `network-security-group__endpoints.rules.subnet_purpose` | private_endpoints | your description |
| `network-security-group__endpoints.rules.default_inbound` | deny_all | rule |
| `network-security-group__endpoints.rules.default_outbound` | deny_internet | forced |
| `network-security-group__endpoints.rules.rules` | {"production": []} | rule |
| `network-security-group__endpoints.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `network-security-group__endpoints.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | rule |
| `network-security-group__integration.rules.subnet_purpose` | app_integration | your description |
| `network-security-group__integration.rules.default_inbound` | deny_all | rule |
| `network-security-group__integration.rules.default_outbound` | azure_default | rule |
| `network-security-group__integration.rules.rules` | {"production": []} | rule |
| `network-security-group__integration.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `network-security-group__integration.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | rule |
| `network-security-group__containerapps.rules.subnet_purpose` | container_apps | your description |
| `network-security-group__containerapps.rules.default_inbound` | deny_all | rule |
| `network-security-group__containerapps.rules.default_outbound` | azure_default | rule |
| `network-security-group__containerapps.rules.rules` | {"production": []} | rule |
| `network-security-group__containerapps.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `network-security-group__containerapps.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | rule |
| `log-analytics-workspace.cost.retention_days` | 30 | inherited |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | inherited |
| `log-analytics-workspace.cost.sku` | PerGB2018 | rule |
| `log-analytics-workspace.access.public_network_access` | enabled | rule |
| `log-analytics-workspace.access.local_auth` | false | inherited |
| `log-analytics-workspace.access.rbac_only_access` | true | rule |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | rule |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | rule |
| `application-insights.component.workspace` | {"production": "log-analytics-workspace"} | inherited |
| `application-insights.component.application_type` | web | rule |
| `application-insights.component.sampling_percentage` | 100 | rule |
| `application-insights.component.daily_cap_gb` | 0 | rule |
| `application-insights.component.store_client_ip` | false | rule |
| `application-insights.networking.public_network_access` | disabled | inherited |
| `application-insights.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__connector", "role": "Monitoring Metrics Publisher"}]} | your description |
| `application-insights.security.local_authentication_disabled` | true | inherited |
| `key-vault.vault.sku` | standard | rule |
| `key-vault.vault.purge_protection` | true | rule |
| `key-vault.vault.soft_delete_retention_days` | 90 | rule |
| `key-vault.vault.rbac_authorization` | true | inherited |
| `key-vault.networking.public_network_access` | disabled | inherited |
| `key-vault.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `key-vault.networking.network_acl_bypass` | None | rule |
| `key-vault.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Key Vault Secrets User"}, {"principal": "user-assigned-identity__connector", "role": "Key Vault Secrets User"}]} | your description |
| `key-vault.security.enabled_for_services` | [] | rule |
| `key-vault.security.secret_placeholders` | ["entra-client-secret"] | your description |
| `key-vault.keys.key_management` | platform_managed | inherited |
| `key-vault.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | rule |
| `key-vault.observability.metrics_enabled` | true | rule |
| `user-assigned-identity__web.identity.purpose` | the web app and the MCP server, to reach models, search, data and secrets | your description |
| `user-assigned-identity__web.identity.federated_credentials` | [] | rule |
| `user-assigned-identity__web.identity.isolation_scope` | None | rule |
| `user-assigned-identity__web.identity.role_assignments` | {"production": []} | rule |
| `user-assigned-identity__connector.identity.purpose` | the document connector function, to index documents and keep its own state | your description |
| `user-assigned-identity__connector.identity.federated_credentials` | [] | rule |
| `user-assigned-identity__connector.identity.isolation_scope` | None | rule |
| `user-assigned-identity__connector.identity.role_assignments` | {"production": []} | rule |
| `user-assigned-identity__runner.identity.purpose` | the code interpreter container app, to pull its image | your description |
| `user-assigned-identity__runner.identity.federated_credentials` | [] | rule |
| `user-assigned-identity__runner.identity.isolation_scope` | None | rule |
| `user-assigned-identity__runner.identity.role_assignments` | {"production": []} | rule |
| `storage-account__uploads.networking.public_network_access` | disabled | inherited |
| `storage-account__uploads.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `storage-account__uploads.networking.private_endpoint_subresources` | ["blob"] | rule |
| `storage-account__uploads.networking.allow_azure_services_bypass` | true | rule |
| `storage-account__uploads.identity.managed_identity` | system_assigned | rule |
| `storage-account__uploads.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Storage Blob Data Contributor"}, {"principal": "search-service", "role": "Storage Blob Data Reader"}]} | your description |
| `storage-account__uploads.security.shared_access_key_enabled` | false | inherited |
| `storage-account__uploads.security.min_tls_version` | TLS1_2 | rule |
| `storage-account__uploads.security.https_traffic_only` | true | rule |
| `storage-account__uploads.security.allow_blob_public_access` | false | rule |
| `storage-account__uploads.security.infrastructure_encryption_enabled` | true | rule |
| `storage-account__uploads.security.key_management` | platform_managed | inherited |
| `storage-account__uploads.security.sftp_enabled` | false | rule |
| `storage-account__uploads.data_protection.replication` | ZRS | derived from your answer |
| `storage-account__uploads.data_protection.access_tier` | Hot | derived from your answer |
| `storage-account__uploads.data_protection.blob_soft_delete_days` | 7 | derived from your answer |
| `storage-account__uploads.data_protection.container_soft_delete_days` | 7 | derived from your answer |
| `storage-account__uploads.data_protection.versioning_enabled` | true | derived from your answer |
| `storage-account__uploads.data_protection.change_feed_enabled` | false | rule |
| `storage-account__uploads.data_protection.point_in_time_restore_days` | 0 | rule |
| `storage-account__uploads.data_protection.immutability` | none | rule |
| `storage-account__uploads.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `storage-account__uploads.observability.diagnostic_categories` | ["audit"] | rule |
| `storage-account__uploads.observability.metrics_enabled` | true | rule |
| `storage-account__host.placement.resource_group` | application | your departure |
| `storage-account__host.networking.public_network_access` | disabled | inherited |
| `storage-account__host.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `storage-account__host.networking.private_endpoint_subresources` | ["blob", "queue", "table"] | forced |
| `storage-account__host.networking.allow_azure_services_bypass` | true | rule |
| `storage-account__host.identity.managed_identity` | system_assigned | rule |
| `storage-account__host.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__connector", "role": "Storage Blob Data Owner"}, {"principal": "user-assigned-identity__connector", "role": "Storage Table Data Contributor"}, {"principal": "user-assigned-identity__connector", "role": "Storage Queue Data Contributor"}]} | your description |
| `storage-account__host.security.shared_access_key_enabled` | false | inherited |
| `storage-account__host.security.min_tls_version` | TLS1_2 | rule |
| `storage-account__host.security.https_traffic_only` | true | rule |
| `storage-account__host.security.allow_blob_public_access` | false | rule |
| `storage-account__host.security.infrastructure_encryption_enabled` | true | rule |
| `storage-account__host.security.key_management` | platform_managed | inherited |
| `storage-account__host.security.sftp_enabled` | false | rule |
| `storage-account__host.data_protection.replication` | ZRS | derived from your answer |
| `storage-account__host.data_protection.access_tier` | Hot | derived from your answer |
| `storage-account__host.data_protection.blob_soft_delete_days` | 7 | derived from your answer |
| `storage-account__host.data_protection.container_soft_delete_days` | 7 | derived from your answer |
| `storage-account__host.data_protection.versioning_enabled` | true | derived from your answer |
| `storage-account__host.data_protection.change_feed_enabled` | false | rule |
| `storage-account__host.data_protection.point_in_time_restore_days` | 0 | rule |
| `storage-account__host.data_protection.immutability` | none | rule |
| `storage-account__host.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `storage-account__host.observability.diagnostic_categories` | ["audit"] | rule |
| `storage-account__host.observability.metrics_enabled` | true | rule |
| `cosmos-db.account.capacity_mode` | provisioned | rule |
| `cosmos-db.account.throughput_mode` | autoscale | rule |
| `cosmos-db.account.max_throughput` | 1000 | rule |
| `cosmos-db.account.total_throughput_limit` | -1 | rule |
| `cosmos-db.account.free_tier` | false | rule |
| `cosmos-db.resilience.zone_redundant` | true | derived from your answer |
| `cosmos-db.resilience.geo_replicas` | {"production": []} | rule |
| `cosmos-db.resilience.automatic_failover` | true | rule |
| `cosmos-db.resilience.consistency_level` | Session | rule |
| `cosmos-db.networking.public_network_access` | disabled | inherited |
| `cosmos-db.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `cosmos-db.networking.network_acl_bypass` | false | rule |
| `cosmos-db.identity.managed_identity` | none | rule |
| `cosmos-db.identity.data_plane_role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Cosmos DB Built-in Data Contributor", "scope": "account"}]} | your description |
| `cosmos-db.identity.role_assignments` | {"production": []} | rule |
| `cosmos-db.security.local_authentication_disabled` | true | inherited |
| `cosmos-db.security.key_based_metadata_writes` | true | inherited |
| `cosmos-db.security.key_management` | platform_managed | inherited |
| `cosmos-db.data_protection.backup_policy` | continuous_7_days | derived from your answer |
| `cosmos-db.data_protection.analytical_storage` | false | rule |
| `cosmos-db.containers.databases` | [{"name": "chatbot", "containers": [{"name": "conversations", "partition_key_paths": ["/userId"]}]}] | your description |
| `cosmos-db.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `cosmos-db.observability.diagnostic_categories` | ["ControlPlaneRequests", "DataPlaneRequests"] | rule |
| `cosmos-db.observability.metrics_enabled` | true | rule |
| `foundry.account.kind` | AIServices | rule |
| `foundry.account.sku_name` | S0 | rule |
| `foundry.account.project_management` | true | rule |
| `foundry.account.projects` | ["chatbot"] | your description |
| `foundry.models.model_deployments` | [{"name": "chat", "format": "OpenAI", "model": "gpt-4.1", "version": "2025-04-14"}, {"name": "embeddings", "format": "OpenAI", "model": "text-embedding-3-large", "version": "1"}] | your description |
| `foundry.models.deployment_sku` | DataZoneStandard | derived from your answer |
| `foundry.models.deployment_capacity` | 10 | rule |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | rule |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | rule |
| `foundry.networking.public_network_access` | disabled | inherited |
| `foundry.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `foundry.networking.restrict_outbound` | true | rule |
| `foundry.identity.managed_identity` | system_assigned | rule |
| `foundry.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Cognitive Services OpenAI User"}, {"principal": "user-assigned-identity__connector", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}]} | your description |
| `foundry.security.local_authentication_disabled` | true | inherited |
| `foundry.security.key_management` | platform_managed | inherited |
| `foundry.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | rule |
| `foundry.observability.metrics_enabled` | true | rule |
| `search-service.service.sku` | standard | rule |
| `search-service.service.replica_count` | 2 | derived from your answer |
| `search-service.service.partition_count` | 1 | rule |
| `search-service.service.semantic_ranker` | free | rule |
| `search-service.networking.public_network_access` | disabled | inherited |
| `search-service.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `search-service.networking.network_rule_bypass` | None | rule |
| `search-service.identity.managed_identity` | system_assigned | rule |
| `search-service.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Search Index Data Reader"}, {"principal": "user-assigned-identity__connector", "role": "Search Index Data Contributor"}]} | your description |
| `search-service.security.local_authentication_disabled` | true | inherited |
| `search-service.security.key_management` | platform_managed | inherited |
| `search-service.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `search-service.observability.diagnostic_categories` | ["OperationLogs"] | rule |
| `search-service.observability.metrics_enabled` | true | rule |
| `container-registry.registry.sku` | Premium | forced |
| `container-registry.registry.zone_redundant` | true | derived from your answer |
| `container-registry.registry.geo_replicas` | {"production": []} | rule |
| `container-registry.registry.retention_untagged_days` | 7 | rule |
| `container-registry.networking.public_network_access` | disabled | inherited |
| `container-registry.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `container-registry.networking.network_rule_bypass` | None | rule |
| `container-registry.networking.export_policy_enabled` | false | rule |
| `container-registry.identity.managed_identity` | none | rule |
| `container-registry.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__runner", "role": "AcrPull"}]} | your description |
| `container-registry.security.admin_enabled` | false | inherited |
| `container-registry.security.anonymous_pull_enabled` | false | rule |
| `container-registry.security.key_management` | platform_managed | inherited |
| `container-registry.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `container-registry.observability.diagnostic_categories` | ["ContainerRegistryRepositoryEvents", "ContainerRegistryLoginEvents"] | rule |
| `container-registry.observability.metrics_enabled` | true | rule |
| `container-apps.environment.workload_profile` | Consumption | rule |
| `container-apps.environment.zone_redundant` | true | derived from your answer |
| `container-apps.environment.internal` | true | inherited |
| `container-apps.environment.infrastructure_subnet` | {"production": "snet-aca"} | forced |
| `container-apps.environment.public_network_access` | disabled | inherited |
| `container-apps.environment.peer_traffic_encryption` | true | rule |
| `container-apps.app.container_image` | container-registry/code-runner:1.0.0 | your description |
| `container-apps.app.container_size` | 0.5-1Gi | rule |
| `container-apps.app.min_replicas` | 2 | derived from your answer |
| `container-apps.app.max_replicas` | 10 | rule |
| `container-apps.app.revision_mode` | Single | rule |
| `container-apps.ingress.ingress` | environment | rule |
| `container-apps.ingress.target_port` | 8080 | your description |
| `container-apps.ingress.allow_insecure` | false | rule |
| `container-apps.identity.managed_identity` | user_assigned | rule |
| `container-apps.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__runner"]} | your description |
| `container-apps.identity.secret_references` | {"production": []} | rule |
| `container-apps.identity.role_assignments` | {"production": []} | rule |
| `container-apps.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `container-apps.observability.diagnostic_categories` | ["ContainerAppConsoleLogs", "ContainerAppSystemLogs"] | rule |
| `container-apps.observability.metrics_enabled` | true | rule |
| `function-app.hosting.plan_type` | flex_consumption | rule |
| `function-app.hosting.runtime_stack` | python | your description |
| `function-app.hosting.runtime_version` | 3.12 | your description |
| `function-app.hosting.zone_redundant` | true | derived from your answer |
| `function-app.hosting.max_instance_count` | 20 | rule |
| `function-app.hosting.always_ready_instances` | 1 | derived from your answer |
| `function-app.hosting.instance_memory_mb` | 2048 | rule |
| `function-app.storage.host_storage_account` | {"production": "storage-account__host"} | your description |
| `function-app.storage.host_storage_auth` | identity | inherited |
| `function-app.storage.deployment_container` | app-package | rule |
| `function-app.networking.public_network_access` | disabled | inherited |
| `function-app.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `function-app.networking.vnet_integration` | true | rule |
| `function-app.networking.integration_subnet` | {"production": "snet-func"} | forced |
| `function-app.networking.vnet_route_all` | true | rule |
| `function-app.identity.managed_identity` | user_assigned | rule |
| `function-app.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__connector"]} | your description |
| `function-app.identity.role_assignments` | {"production": []} | rule |
| `function-app.security.https_only` | true | rule |
| `function-app.security.min_tls_version` | 1.2 | rule |
| `function-app.security.basic_auth_enabled` | false | inherited |
| `function-app.security.application_insights` | {"production": "application-insights"} | your description |
| `function-app.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `function-app.observability.diagnostic_categories` | ["FunctionAppLogs", "AppServiceAuditLogs"] | rule |
| `function-app.observability.metrics_enabled` | true | rule |
| `app-service__web.hosting.os_type` | Linux | rule |
| `app-service__web.hosting.sku` | P1v3 | rule |
| `app-service__web.hosting.zone_redundant` | true | derived from your answer |
| `app-service__web.hosting.instance_count` | 2 | derived from your answer |
| `app-service__web.networking.public_network_access` | disabled | inherited |
| `app-service__web.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `app-service__web.networking.vnet_integration` | true | rule |
| `app-service__web.networking.integration_subnet` | {"production": "snet-web"} | forced |
| `app-service__web.networking.vnet_route_all` | true | rule |
| `app-service__web.identity.managed_identity` | user_assigned | your description |
| `app-service__web.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__web"]} | your description |
| `app-service__web.security.https_only` | true | rule |
| `app-service__web.security.min_tls_version` | 1.2 | rule |
| `app-service__web.security.ftps_state` | Disabled | rule |
| `app-service__web.security.basic_auth_enabled` | false | inherited |
| `app-service__web.runtime.runtime_stack` | python | your description |
| `app-service__web.runtime.runtime_version` | 3.12 | your description |
| `app-service__web.runtime.always_on` | true | rule |
| `app-service__web.runtime.health_check_path` |  | rule |
| `app-service__web.runtime.http2_enabled` | true | rule |
| `app-service__web.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `app-service__web.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | rule |
| `app-service__web.observability.metrics_enabled` | true | rule |
| `app-service__mcp.hosting.os_type` | Linux | rule |
| `app-service__mcp.hosting.sku` | P1v3 | rule |
| `app-service__mcp.hosting.zone_redundant` | true | derived from your answer |
| `app-service__mcp.hosting.instance_count` | 2 | derived from your answer |
| `app-service__mcp.networking.public_network_access` | disabled | inherited |
| `app-service__mcp.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | forced |
| `app-service__mcp.networking.vnet_integration` | true | rule |
| `app-service__mcp.networking.integration_subnet` | {"production": "snet-mcp"} | forced |
| `app-service__mcp.networking.vnet_route_all` | true | rule |
| `app-service__mcp.identity.managed_identity` | user_assigned | your description |
| `app-service__mcp.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__web"]} | your description |
| `app-service__mcp.security.https_only` | true | rule |
| `app-service__mcp.security.min_tls_version` | 1.2 | rule |
| `app-service__mcp.security.ftps_state` | Disabled | rule |
| `app-service__mcp.security.basic_auth_enabled` | false | inherited |
| `app-service__mcp.runtime.runtime_stack` | node | your description |
| `app-service__mcp.runtime.runtime_version` | 22-lts | your description |
| `app-service__mcp.runtime.always_on` | true | rule |
| `app-service__mcp.runtime.health_check_path` |  | rule |
| `app-service__mcp.runtime.http2_enabled` | true | rule |
| `app-service__mcp.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | inherited |
| `app-service__mcp.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | rule |
| `app-service__mcp.observability.metrics_enabled` | true | rule |
| `wiring.access` | [{"from": "users", "to": "app-service__web", "label": "HTTPS 443"}, {"from": "app-service__web", "to": "external:entra-id", "label": "sign-in"}, {"from": "app-service__web", "to": "app-service__mcp"}, {"from": "app-service__web", "to": "foundry"}, {"from": "app-service__web", "to": "search-service"}, {"from": "app-service__web", "to": "cosmos-db"}, {"from": "app-service__web", "to": "storage-account__uploads"}, {"from": "app-service__web", "to": "key-vault"}, {"from": "app-service__mcp", "to": "container-apps"}, {"from": "app-service__mcp", "to": "foundry"}, {"from": "function-app", "to": "search-service"}, {"from": "function-app", "to": "foundry"}, {"from": "function-app", "to": "key-vault"}, {"from": "function-app", "to": "storage-account__host"}, {"from": "function-app", "to": "application-insights"}, {"from": "container-apps", "to": "container-registry", "label": "pulls its image"}] | your description |
| `wiring.purposes` | {"app-service__web": "Chat front end and back end", "app-service__mcp": "MCP tool server", "function-app": "Connector to the document store", "container-apps": "Code interpreter", "foundry": "Chat and embedding models", "search-service": "Search; indexes the uploads, embeds with the models", "cosmos-db": "Conversation history", "storage-account__uploads": "Uploaded files", "storage-account__host": "State of the connector function", "key-vault": "Secrets", "user-assigned-identity__web": "Web app and MCP server", "user-assigned-identity__connector": "Connector function", "user-assigned-identity__runner": "Code interpreter", "network-security-group__endpoints": "Private endpoints subnet", "network-security-group__integration": "App integration subnets", "network-security-group__containerapps": "Container Apps subnet", "container-registry": "Images of all apps", "application-insights": "Application telemetry"} | your description |
| `wiring.optional` | [] | rule |
