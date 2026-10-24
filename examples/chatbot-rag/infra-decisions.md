# Decisions for "chatrag"

What will be built, decided from your answers and the rules behind the defaults. Every line is one decision; the key in the appendix is where an engineer finds it in the specification.

As of 2026-10-24. Specification: `infra-spec.yaml`.

## The system

- The system is deployed in these stages: development, test, live operation.
- Everything runs in the Azure region westeurope.
- "chatrag" is the name every part of the system carries.
- Each stage lives in its own subscription, so the stages cannot touch each other's resources, budgets or permissions.

## What differs between the stages

One code base is deployed through these stages; everything not listed here is identical in every stage.

- Logs are collected in development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Virtual Network: Custom name servers: development: none; test: none; live operation: none (none: Azure's own).
- Azure Virtual Network: Subnets that will get a security group: development: snet-endpoints, snet-web; test: snet-endpoints, snet-web; live operation: snet-endpoints, snet-web.
- Azure Virtual Network: Network logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Network Security Group (endpoints): Traffic allowed explicitly: development: none; test: none; live operation: none.
- Azure Network Security Group (endpoints): Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Network Security Group (integration): Traffic allowed explicitly: development: none; test: none; live operation: none.
- Azure Network Security Group (integration): Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Application Insights (workspace-based): Its telemetry is stored in development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Application Insights (workspace-based): Access rights on the component granted to: development: app-service (Monitoring Metrics Publisher); test: app-service (Monitoring Metrics Publisher); live operation: app-service (Monitoring Metrics Publisher).
- Azure Key Vault: Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints.
- Azure Key Vault: Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure Storage Account: Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints.
- Azure Storage Account: Access rights granted to: development: search-service (Storage Blob Data Reader); test: search-service (Storage Blob Data Reader); live operation: search-service (Storage Blob Data Reader).
- Azure Storage Account: Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure AI Foundry (AI Services account with projects and model deployments): Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints.
- Azure AI Foundry (AI Services account with projects and model deployments): Access rights on the account granted to: development: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); test: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); live operation: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
- Azure AI Foundry (AI Services account with projects and model deployments): Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure AI Search service: The search service is the development: basic, small and cheap, one partition; test: basic, small and cheap, one partition; live operation: standard, the normal production tier tier. _(cheaper outside production)_
- Azure AI Search service: Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints.
- Azure AI Search service: Access rights on the search service granted to: development: app-service (Search Index Data Reader); test: app-service (Search Index Data Reader); live operation: app-service (Search Index Data Reader).
- Azure AI Search service: Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Azure App Service (web app on an App Service plan): The hosting plan is size development: B1, small and cheap, no zone redundancy - for stages nobody depends on; test: B1, small and cheap, no zone redundancy - for stages nobody depends on; live operation: P1v3, premium, the normal production size. _(cheaper outside production)_
- Azure App Service (web app on an App Service plan): Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints.
- Azure App Service (web app on an App Service plan): Outgoing traffic leaves through the subnet development: snet-web; test: snet-web; live operation: snet-web.
- Azure App Service (web app on an App Service plan): Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.

## What follows from your answers

- **The system is deployed by GitHub Actions.** _(from your description)_
- **A day's outage would be tolerable.** _(from your description)_
  - therefore, Azure Storage Account: The data is kept three times in one datacenter.
  - therefore, Azure AI Search service: 1 copies of the index answer queries.
  - therefore, Azure App Service (web app on an App Service plan): The app does not survive the loss of one datacenter of the region.
  - therefore, Azure App Service (web app on an App Service plan): Copies of the app running at the same time: 1.
- **After a mistaken delete you must be able to go back a week.** _(not said, so the usual answer applies)_
  - therefore, Azure Storage Account: Deleted files can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account: Deleted folders can be restored for 7 days (0: not at all).
  - therefore, Azure Storage Account: Earlier versions of overwritten files are kept.
- **The data is worked with all the time.** _(not said, so the usual answer applies)_
  - therefore, Azure Storage Account: Stored in the standard - cheap to read, for data in use class.
- **Against deliberate destruction the data is protected only inside the system itself - whoever can delete the system can delete the copies.** _(not said, so the usual answer applies)_
- **The data is stored and processed only inside the region's economic area, for example the EU.** _(not said, so the usual answer applies)_
  - therefore, Azure AI Foundry (AI Services account with projects and model deployments): Requests to the models are processed anywhere inside the same data zone (for example the EU).
- **The code is built from resources written out individually.** _(your answer)_
- **Access is private only - nothing is reachable from the internet.** _(from your description)_
- **Rules to comply with: none.** _(from your description)_
- **Logs are kept for 30 days.** _(not said, so the usual answer applies)_

## Set by the rules

Nothing here was asked; each follows a rule or one of the answers above. Say so if one is wrong.

### For the whole system

- The pipeline signs in to Azure with a short-lived token issued per run, no password stored anywhere.
- A person approves the change before it is applied: in live operation only.
- The system lands in its own environment: there is no shared platform, so it brings its own network, name resolution and logging.
- Passwords and access keys are switched off; access goes through company accounts, so every action is attributable.
- Encryption keys are protected in software - the standard, sufficient unless a mandate names hardware.
- Encryption keys are managed by Azure - encrypted, rotated, no effort on your side.
- The network is built by this deployment.
- Name resolution for private connections is handled by this deployment itself. — because: The system lands in its own environment: there is no shared platform, so it brings its own network, name resolution and logging.
- Logs go to a workspace this deployment creates and pays for. — because: The system lands in its own environment: there is no shared platform, so it brings its own network, name resolution and logging.
- Logs are collected in development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace. — because: Logs go to a workspace this deployment creates and pays for.
- Daily log intake cap: -1 GB (-1: no cap).

### Azure Virtual Network

- Custom name servers: development: none; test: none; live operation: none (none: Azure's own).
- Network rules apply to private connections in their subnet.
- Shortcuts to Azure services from the subnets: none.
- Subnets handed to a service: snet-web (Microsoft.Web/serverFarms). — because: `resources.app-service.networking.integration_subnet`
- A paid DDoS protection plan is not used; Azure's basic protection applies either way.
- Subnets that will get a security group: development: snet-endpoints, snet-web; test: snet-endpoints, snet-web; live operation: snet-endpoints, snet-web. — because: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Network logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- A record of allowed and denied traffic is not kept.

### Azure Network Security Group (endpoints)

- The group guards a subnet for private connections to Azure services.
- Inbound traffic that no rule allows is refused, including traffic from other machines in the same network.
- Outbound traffic to the internet that no rule allows is refused; what must go out goes through the company firewall. — because: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Traffic allowed explicitly: development: none; test: none; live operation: none.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: which rule was applied to which machine, how often each rule matched.

### Azure Network Security Group (integration)

- The group guards a subnet for the outgoing traffic of web and function apps.
- Inbound traffic that no rule allows is refused, including traffic from other machines in the same network.
- Outbound traffic to the internet that no rule allows is left to Azure's built-in rules, which let it out.
- Traffic allowed explicitly: development: none; test: none; live operation: none.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: which rule was applied to which machine, how often each rule matched.

### Azure Log Analytics Workspace

- Logs are kept for 30 days.
- Daily log intake cap: -1 GB (-1: no cap).
- Billed per gigabyte, pay as you go.
- The log workspace is reachable from the internet, with company accounts and encryption - there is no private link scope to go through.
- Sending logs with the workspace key is not possible - agents use company identities.
- Who may read logs is decided by the workspace's own permissions.
- A deleted workspace can be recovered for 14 days.
- Long-term archiving to cheap storage is off.

### Azure Application Insights (workspace-based)

- Its telemetry is stored in development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- The component is set up for a web application or a service.
- 100 percent of the telemetry is kept.
- Daily telemetry cap for this component: 0 GB (0: no cap).
- Visitors' IP addresses are masked and not stored.
- The component is reachable only through the private monitoring connection, for sending and for reading.
- Sending telemetry with only a key is switched off; applications sign in with company identities.

### Azure Key Vault

- The vault is the standard, keys protected in software tier.
- A deleted vault or secret cannot be wiped, not even by an administrator before its retention ends.
- Deleted vault contents can be restored for 90 days.
- Access to the vault's contents is controlled by role assignments, like everything else in Azure.
- The vault is not reachable from the internet at all.
- Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the vault's firewall.
- Platform services allowed to read from the vault: none (empty: none).
- Empty slots are created for the secrets none; their values are entered afterwards by hand or by the workload.
- Encryption keys are managed by Azure - the vault holds none for encryption.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: every read, write and failed access to the vault, how policies judged the vault.
- Usage and performance figures are collected.

### Azure Storage Account

- The storage is not reachable from the internet at all.
- Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints. — because: The network is built by this deployment.
- Private connections exist for: files (blob).
- Azure's own services (backup, monitoring) may reach the storage past the firewall.
- The storage has its own identity for reaching other services.
- Access rights granted to: development: search-service (Storage Blob Data Reader); test: search-service (Storage Blob Data Reader); live operation: search-service (Storage Blob Data Reader).
- Access with a shared key is not possible; access goes through company accounts.
- Connections must use at least TLS 1.2 encryption.
- Unencrypted connections are refused.
- Making individual folders publicly readable is not possible.
- A second encryption layer below the service is on.
- Encryption keys are managed by Azure - encrypted, rotated, no effort on your side.
- File transfer via SFTP is off.
- A log of every change is not kept.
- The whole storage can be rewound 0 days (0: not at all).
- Deletion protection by law or policy: none.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: who accessed what.
- Usage and performance figures are collected.

### Azure AI Foundry (AI Services account with projects and model deployments)

- The account is an AI Foundry resource, which also offers projects, agents and the other AI services.
- The account uses the pricing tier S0, the standard paid tier - the only one that has projects and private endpoints in production.
- The account holds Foundry projects, as containers for access, data and cost.
- The account holds the projects none.
- Each model may process up to 10 thousand tokens per minute.
- When the model version expires, it moves to the new default version on that day.
- Prompts and answers are checked by the content filter Microsoft.DefaultV2.
- The account is not reachable from the internet at all.
- Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints. — because: The network is built by this deployment.
- The account may call out only to addresses that are explicitly allowed.
- The account has its own identity.
- Access rights on the account granted to: development: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); test: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); live operation: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
- Signing in with account keys is switched off; access goes through company accounts.
- Encryption keys are managed by Azure - encrypted, rotated, no effort on your side.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: changes to the account and who made them, every request to the models, with its caller, size and result (not the text), the tokens each call used.
- Usage and performance figures are collected.

### Azure AI Search service

- The search service is the development: basic, small and cheap, one partition; test: basic, small and cheap, one partition; live operation: standard, the normal production tier tier.
- The index data is spread over 1 partition(s).
- Re-ranking of results by meaning is on, within a small free monthly allowance.
- The search service is not reachable from the internet at all.
- Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints. — because: The network is built by this deployment.
- Trusted Azure services may not pass past the search service's firewall.
- The search service has its own identity.
- Access rights on the search service granted to: development: app-service (Search Index Data Reader); test: app-service (Search Index Data Reader); live operation: app-service (Search Index Data Reader).
- Signing in with API keys is switched off; access goes through company accounts.
- Encryption keys are managed by Azure - encrypted, rotated, no effort on your side.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: every query and every change to indexes and indexers.
- Usage and performance figures are collected.

### Azure App Service (web app on an App Service plan)

- The app runs on Linux.
- The hosting plan is size development: B1, small and cheap, no zone redundancy - for stages nobody depends on; test: B1, small and cheap, no zone redundancy - for stages nobody depends on; live operation: P1v3, premium, the normal production size.
- The app is not reachable from the internet at all.
- Its private connection lands in subnet development: snet-endpoints; test: snet-endpoints; live operation: snet-endpoints. — because: The network is built by this deployment.
- The app's own outgoing traffic goes through the company network, so it can reach private services.
- Outgoing traffic leaves through the subnet development: snet-web; test: snet-web; live operation: snet-web. — because: The network is built by this deployment.
- Outgoing traffic is routed entirely through the company network, including to the internet.
- The app has its own identity for reaching other services.
- Unencrypted connections are redirected to the encrypted address.
- Connections must use at least TLS 1.2 encryption.
- File upload by FTP is switched off.
- Deploying with a user name and password is not possible; deployments run through company accounts.
- The app stays loaded and answers the first request at once when there is no traffic.
- The platform checks the app's health at the path  (empty: not checked).
- HTTP/2 is on.
- Its logs go to development: log-analytics-workspace; test: log-analytics-workspace; live operation: log-analytics-workspace.
- Logged: every web request, the app's own log messages, who signed in to deploy or manage the app, changes to the access restrictions, the platform's own messages about the app.
- Usage and performance figures are collected.

## Still open

Nothing can be deployed until these are answered.

- Which subscription does each stage deploy into? One per stage (stage_isolation: subscription). [development, test, live operation] _(needed from: workload owner)_ — blocks: apply
- Which resource group does each stage deploy into? [development, test, live operation] _(needed from: workload owner)_ — blocks: apply
- Which tag set does the organisation apply? Nothing stated, no repository to read it from. _(needed from: workload owner)_ — blocks: apply
- Which address range does each stage's new virtual network get? [development, test, live operation] _(needed from: network / IPAM owner)_ — blocks: apply
- Which prefix inside that range is the private endpoint subnet (snet-endpoints)? [development, test, live operation] _(needed from: network / IPAM owner)_ — blocks: apply
- Prefixes of the subnets snet-endpoints (private endpoints) and snet-web (App Service integration, delegated to Microsoft.Web/serverFarms), per stage. [development, test, live operation] _(needed from: network / IPAM owner)_ — blocks: apply
- Which chat model and which embedding model (name and version)? Regional, with quota - looked up at render time, never recalled. _(needed from: workload owner)_ — blocks: apply
- Is there quota for the chosen models as DataZoneStandard in West Europe at 10,000 tokens per minute each? Not checked; a deployment beyond the quota fails at apply. _(needed from: workload owner)_ — blocks: apply
- Which runtime stack and version does the web app run (runtime_stack and runtime_version)? _(needed from: workload owner)_ — blocks: apply
- Which Azure Monitor Private Link Scope should the component belong to? Standalone: none exists, so it is built or the component stays open. _(needed from: workload owner)_ — blocks: apply
- Which principal reads which secrets? Nothing stated; with RBAC-only access a vault without assignment is working as specified and unusable. _(needed from: workload owner)_ — blocks: apply
- Who uploads the documents, and which data-plane role does that principal need? Only the search service (reader) is assigned. _(needed from: workload owner)_ — blocks: apply
- The search indexer reaches the storage account over a shared private link, approved on the account. Not rendered: wiring between two resources that no question set owns. _(needed from: workload owner)_ — blocks: apply

## Placeholders

Values the run chose to keep going. They are not decisions yet.

- Access rights on the component granted to: development: app-service (Monitoring Metrics Publisher); test: app-service (Monitoring Metrics Publisher); live operation: app-service (Monitoring Metrics Publisher). (`resources.application-insights.identity.role_assignments`)

## Appendix: every decision

| Key | Value | Source |
|---|---|---|
| `deployment.naming_convention` | default | rule |
| `deployment.module_source` | authored | your answer |
| `deployment.deploy_mechanism` | github | your description |
| `deployment.pipeline_auth` | workload_identity | rule |
| `deployment.pipeline_approvals` | production | rule |
| `deployment.stage_isolation` | subscription | rule |
| `deployment.non_production_savings` | enabled | rule |
| `deployment.outage_impact` | tolerable | your description |
| `deployment.data_loss_tolerance` | one_week | rule |
| `deployment.data_access_pattern` | active | rule |
| `deployment.backup_isolation` | operational | rule |
| `deployment.data_residency` | data_zone | rule |
| `deployment.landing_zone` | standalone | your description |
| `deployment.network_exposure` | private | your description |
| `deployment.local_auth` | disabled | rule |
| `deployment.mandates` | [] | your description |
| `deployment.key_protection` | software | rule |
| `deployment.key_management` | platform_managed | rule |
| `deployment.network_ownership` | create | your description |
| `deployment.private_dns_ownership` | deployment | forced |
| `deployment.observability_ownership` | create | forced |
| `deployment.diagnostics_destination` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | forced |
| `deployment.log_retention_days` | 30 | rule |
| `deployment.daily_quota_gb` | -1 | rule |
| `virtual-network.addressing.dns_servers` | {"development": [], "test": [], "production": []} | rule |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | rule |
| `virtual-network.subnet_policy.service_endpoints` | [] | rule |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "snet-web", "service": "Microsoft.Web/serverFarms"}] | forced |
| `virtual-network.security.ddos_protection` | false | rule |
| `virtual-network.security.subnets_expecting_nsg` | {"development": ["snet-endpoints", "snet-web"], "test": ["snet-endpoints", "snet-web"], "production": ["snet-endpoints", "snet-web"]} | forced |
| `virtual-network.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `virtual-network.observability.flow_logs_enabled` | false | rule |
| `network-security-group__endpoints.rules.subnet_purpose` | private_endpoints | your description |
| `network-security-group__endpoints.rules.default_inbound` | deny_all | rule |
| `network-security-group__endpoints.rules.default_outbound` | deny_internet | forced |
| `network-security-group__endpoints.rules.rules` | {"development": [], "test": [], "production": []} | rule |
| `network-security-group__endpoints.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `network-security-group__endpoints.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | rule |
| `network-security-group__integration.rules.subnet_purpose` | app_integration | your description |
| `network-security-group__integration.rules.default_inbound` | deny_all | rule |
| `network-security-group__integration.rules.default_outbound` | azure_default | rule |
| `network-security-group__integration.rules.rules` | {"development": [], "test": [], "production": []} | rule |
| `network-security-group__integration.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `network-security-group__integration.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | rule |
| `log-analytics-workspace.cost.retention_days` | 30 | inherited |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | inherited |
| `log-analytics-workspace.cost.sku` | PerGB2018 | rule |
| `log-analytics-workspace.access.public_network_access` | enabled | rule |
| `log-analytics-workspace.access.local_auth` | false | inherited |
| `log-analytics-workspace.access.rbac_only_access` | true | rule |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | rule |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | rule |
| `application-insights.component.workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `application-insights.component.application_type` | web | rule |
| `application-insights.component.sampling_percentage` | 100 | rule |
| `application-insights.component.daily_cap_gb` | 0 | rule |
| `application-insights.component.store_client_ip` | false | rule |
| `application-insights.networking.public_network_access` | disabled | inherited |
| `application-insights.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}], "test": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}], "production": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}]} | placeholder |
| `application-insights.security.local_authentication_disabled` | true | inherited |
| `key-vault.vault.sku` | standard | rule |
| `key-vault.vault.purge_protection` | true | rule |
| `key-vault.vault.soft_delete_retention_days` | 90 | rule |
| `key-vault.vault.rbac_authorization` | true | inherited |
| `key-vault.networking.public_network_access` | disabled | inherited |
| `key-vault.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | forced |
| `key-vault.networking.network_acl_bypass` | None | rule |
| `key-vault.security.enabled_for_services` | [] | rule |
| `key-vault.security.secret_placeholders` | [] | rule |
| `key-vault.keys.key_management` | platform_managed | inherited |
| `key-vault.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | rule |
| `key-vault.observability.metrics_enabled` | true | rule |
| `storage-account.networking.public_network_access` | disabled | inherited |
| `storage-account.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | forced |
| `storage-account.networking.private_endpoint_subresources` | ["blob"] | rule |
| `storage-account.networking.allow_azure_services_bypass` | true | rule |
| `storage-account.identity.managed_identity` | system_assigned | rule |
| `storage-account.identity.role_assignments` | {"development": [{"principal": "search-service", "role": "Storage Blob Data Reader"}], "test": [{"principal": "search-service", "role": "Storage Blob Data Reader"}], "production": [{"principal": "search-service", "role": "Storage Blob Data Reader"}]} | your answer |
| `storage-account.security.shared_access_key_enabled` | false | inherited |
| `storage-account.security.min_tls_version` | TLS1_2 | rule |
| `storage-account.security.https_traffic_only` | true | rule |
| `storage-account.security.allow_blob_public_access` | false | rule |
| `storage-account.security.infrastructure_encryption_enabled` | true | rule |
| `storage-account.security.key_management` | platform_managed | inherited |
| `storage-account.security.sftp_enabled` | false | rule |
| `storage-account.data_protection.replication` | LRS | derived from your answer |
| `storage-account.data_protection.access_tier` | Hot | derived from your answer |
| `storage-account.data_protection.blob_soft_delete_days` | 7 | derived from your answer |
| `storage-account.data_protection.container_soft_delete_days` | 7 | derived from your answer |
| `storage-account.data_protection.versioning_enabled` | true | derived from your answer |
| `storage-account.data_protection.change_feed_enabled` | false | rule |
| `storage-account.data_protection.point_in_time_restore_days` | 0 | rule |
| `storage-account.data_protection.immutability` | none | rule |
| `storage-account.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `storage-account.observability.diagnostic_categories` | ["audit"] | rule |
| `storage-account.observability.metrics_enabled` | true | rule |
| `foundry.account.kind` | AIServices | rule |
| `foundry.account.sku_name` | S0 | rule |
| `foundry.account.project_management` | true | rule |
| `foundry.account.projects` | [] | rule |
| `foundry.models.deployment_sku` | DataZoneStandard | derived from your answer |
| `foundry.models.deployment_capacity` | 10 | rule |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | rule |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | rule |
| `foundry.networking.public_network_access` | disabled | inherited |
| `foundry.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | forced |
| `foundry.networking.restrict_outbound` | true | rule |
| `foundry.identity.managed_identity` | system_assigned | rule |
| `foundry.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}], "test": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}], "production": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}]} | your description |
| `foundry.security.local_authentication_disabled` | true | inherited |
| `foundry.security.key_management` | platform_managed | inherited |
| `foundry.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | rule |
| `foundry.observability.metrics_enabled` | true | rule |
| `search-service.service.sku` | {"development": "basic", "test": "basic", "production": "standard"} | rule |
| `search-service.service.replica_count` | 1 | derived from your answer |
| `search-service.service.partition_count` | 1 | rule |
| `search-service.service.semantic_ranker` | free | rule |
| `search-service.networking.public_network_access` | disabled | inherited |
| `search-service.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | forced |
| `search-service.networking.network_rule_bypass` | None | rule |
| `search-service.identity.managed_identity` | system_assigned | rule |
| `search-service.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Search Index Data Reader"}], "test": [{"principal": "app-service", "role": "Search Index Data Reader"}], "production": [{"principal": "app-service", "role": "Search Index Data Reader"}]} | your description |
| `search-service.security.local_authentication_disabled` | true | inherited |
| `search-service.security.key_management` | platform_managed | inherited |
| `search-service.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `search-service.observability.diagnostic_categories` | ["OperationLogs"] | rule |
| `search-service.observability.metrics_enabled` | true | rule |
| `app-service.hosting.os_type` | Linux | rule |
| `app-service.hosting.sku` | {"development": "B1", "test": "B1", "production": "P1v3"} | rule |
| `app-service.hosting.zone_redundant` | false | derived from your answer |
| `app-service.hosting.instance_count` | 1 | derived from your answer |
| `app-service.networking.public_network_access` | disabled | inherited |
| `app-service.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | forced |
| `app-service.networking.vnet_integration` | true | rule |
| `app-service.networking.integration_subnet` | {"development": "snet-web", "test": "snet-web", "production": "snet-web"} | forced |
| `app-service.networking.vnet_route_all` | true | rule |
| `app-service.identity.managed_identity` | system_assigned | rule |
| `app-service.security.https_only` | true | rule |
| `app-service.security.min_tls_version` | 1.2 | rule |
| `app-service.security.ftps_state` | Disabled | rule |
| `app-service.security.basic_auth_enabled` | false | inherited |
| `app-service.runtime.always_on` | true | rule |
| `app-service.runtime.health_check_path` |  | rule |
| `app-service.runtime.http2_enabled` | true | rule |
| `app-service.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | inherited |
| `app-service.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | rule |
| `app-service.observability.metrics_enabled` | true | rule |
| `wiring.private_dns_zones` | ["privatelink.blob.core.windows.net", "privatelink.vaultcore.azure.net", "privatelink.cognitiveservices.azure.com", "privatelink.openai.azure.com", "privatelink.services.ai.azure.com", "privatelink.search.windows.net", "privatelink.azurewebsites.net", "privatelink.monitor.azure.com"] | forced |
| `wiring.access` | [{"from": "users", "to": "app-service", "label": "HTTPS 443"}, {"from": "app-service", "to": "foundry"}, {"from": "app-service", "to": "search-service"}, {"from": "search-service", "to": "storage-account", "label": "indexer"}, {"from": "search-service", "to": "foundry", "label": "embeddings"}] | your description |
| `wiring.purposes` | {"app-service": "Chat web app", "foundry": "Chat and embedding models", "search-service": "Retrieval index over the documents", "storage-account": "Source documents", "key-vault": "Secrets of the app", "application-insights": "Application telemetry", "network-security-group__endpoints": "Private endpoints subnet", "network-security-group__integration": "App integration subnet"} | your description |
| `wiring.optional` | [] | rule |
