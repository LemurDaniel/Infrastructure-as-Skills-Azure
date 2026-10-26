# Azure Machine Learning workspace - what the question set cannot express

## Fixed at creation

- **The storage account and the key vault.** Bound to the workspace for its lifetime; the
  Application Insights component and the container registry can be replaced later but not
  removed.
- **The HBI flag**, the **customer-managed key** and **service-side encryption**.
- **Managed network isolation can only tighten.** `disabled` to a managed mode works later;
  back to `disabled` never.
- **The name and the region.**

## Ordering

The storage account (GPv2, no hierarchical namespace, blob and file private endpoints, same
region), the key vault (RBAC, purge protection, same region), Application Insights on the
deployment's Log Analytics workspace, the container registry (Premium for a private endpoint,
admin user off), the user-assigned identity with its roles on all four when `user_assigned`,
then the workspace with `provision_network_now`, then the computes, the image-build compute
set on a second apply, then the data scientists' roles on the workspace **and** on the storage
account (identity-based datastores need `Storage Blob Data Contributor` per user), then the
managed online endpoints and jobs from the team's own pipeline. The private DNS zones
(`privatelink.api.azureml.ms`, `privatelink.notebooks.azure.net`) before the private endpoint
is used.

## Pitfalls

**Null dependencies make the Terraform module create them.** `storage_account`, `key_vault`,
`application_insights` and `container_registry` with a null `resource_id` are created by the
module with its own defaults - public, keyed, in the workspace's group - and no set owns them.
The ids are always passed; the Bicep module requires the first three for `Default`.

**The default registry is the leak.** With no `container_registry` the service creates a Basic
registry with the admin user enabled on the first environment build. A private deployment names
a Premium registry and an `image_build_compute` inside the workspace, or image builds fail with
a pull error after a clean deployment.

**The first FQDN rule buys a firewall.** `outbound_fqdns` with one entry makes the managed
network provision an Azure Firewall (Standard unless `firewallSku: Basic`), billed by the hour.
Private-endpoint rules to other Azure resources do not. A package feed inside the network
removes the need.

**Approved-outbound blocks the obvious.** `pip install` from the internet, Hugging Face downloads,
`conda` channels: each needs an FQDN rule or a mirror. The first job after deployment is where
the list gets written; `provision_network_now` moves the network errors into the apply.

**Identity-based datastores change who needs which role.** With `storage_datastore_auth:
identity` every user who browses data in the studio needs `Storage Blob Data Contributor` on the
storage account, not only the workspace identity - a role list the storage account's
`role_assignments` carries, through the pattern.

**User-assigned identity means the roles come first.** Blob and file data roles on storage, the
vault role, `AcrPull`/`AcrPush`, `Monitoring Metrics Publisher` on Application Insights and
`Contributor` on the resource group for the managed resources; a missing one fails the first job
or the first endpoint, not the deployment.

**The private endpoint writes two zones.** API and notebooks; a platform holding only the first
gives a studio that loads and notebooks that do not open.

**The log category list is long and moves.** The set offers twelve; the full list (read and
change events per asset type, inference events) is checked against
`az monitor diagnostic-settings categories list --resource <workspace id>` before a render.

**The modules disagree with each other and with the guardrails.** Isolation (Terraform
`Disabled`, Bicep unset), datastore auth (Terraform `identity`, Bicep unset = key), identity
(Bicep defaults to system-assigned, Terraform to none), `sku` (Bicep requires it, Terraform has no
input). Every decision is written.

## Not covered here, and why

Compute sizing and quota, online and batch endpoints and their deployments, datastores beyond
the defaults, connections, feature stores (kind `FeatureStore`), registries, the Foundry hub and
project kinds (replaced by the foundry set), attached Kubernetes and Synapse Spark, and
bring-your-own-VNet compute injection (`disabled` isolation with subnets per compute) have no
question set; a request for one is said out loud, not improvised.
