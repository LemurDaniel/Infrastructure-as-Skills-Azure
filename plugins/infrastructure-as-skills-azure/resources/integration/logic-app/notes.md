# Logic Apps - what the question set cannot express

## Fixed at creation

- **The hosting model.** Standard (`Microsoft.Web/sites`, kind `functionapp,workflowapp`) and
  Consumption (`Microsoft.Logic/workflows`) are different resource types; moving is a
  re-authoring of the workflows into the other runtime, not an edit.
- **The plan's zone redundancy** and its operating system. A Workflow Standard plan hosts logic
  apps only; it cannot be shared with web or function apps.
- **The Standard app's storage account.** The host's queues, tables and the content share are
  bound to it; switching accounts loses run history and trigger state.
- **The name.** A Standard site name is global and is the hostname; a Consumption workflow name
  is unique in its resource group and part of every trigger URL.
- **The region.**

## Ordering

The user-assigned identity, its roles on the host storage account (`Storage Blob Data Owner`,
`Storage Queue Data Contributor`, `Storage Table Data Contributor`; the file share needs the
connection string in Key Vault and the identity `Key Vault Secrets User` on it), the storage
account with private endpoints for **blob, queue, table and file**, the plan, the site, then the
workflows from the integration team's pipeline, then the API connections and their authorisation,
then the roles of the identity on what the connections reach. Consumption: identity, roles,
workflow resources, then the definitions. The workspace before the diagnostic setting.

## Pitfalls

**The Terraform site module renders the storage key for a logic app, and nothing overrides it.**
For `kind = "logicapp"` the module requires `storage_account_access_key` and writes
`AzureWebJobsStorage` as a key connection string *after* `app_settings`, without the override
guard its function-app path has. `host_storage_auth: identity` therefore renders the Standard
site authored (an `azapi_resource` with its `appsettings` child) and the spec records the forced
departure; the module path is for `key`. The Bicep module writes no logic-app settings at all, so
the render owns every host setting there, including the extension bundle. A module release can
change either; re-read the pinned README.

**The content share is the one place a key remains.** Blob, queue and table connections take the
managed identity; the Azure Files share that holds the app content is mounted with a connection
string. Keep it in Key Vault as a reference, keep shared-key access on the storage account **on**
(the share needs it) with the key rotated by the vault, and name it in the handover - a storage
set that renders `shared_access_key_enabled: false` for this account breaks the app at start.

**A private storage account needs VNet integration and `vnet_route_all`.** The host reaches its
storage over the integration subnet; without integration, or with only private-range routing and
public DNS for the account, the app does not start and the error names storage, not networking.
The private endpoint on the app itself is for inbound only.

**Consumption has no `disabled`.** Trigger URLs are public; the controls are the IP ranges and
the open-authentication policy. A private deployment that insists on Consumption records the
departure on the workflow, and the request triggers are Entra-only so a leaked URL is harmless.

**The SAS switch is new.** Disabling shared access signatures on request triggers is a property
that arrived after both modules' typed inputs; the Consumption module takes `access_control` as an
untyped map in ARM spelling, so the property name is read from the ARM reference before a render
and the Standard host setting from the Logic Apps Standard reference.

**The modules disagree with each other and with the guardrails.** Terraform's site module defaults
TLS to 1.3 and SCM basic auth to on, the plan module to `P1v2`; Bicep's site module writes no host
settings; the workflow modules default `state` to `Enabled` in both. Every decision is written.

**Connections are not infrastructure, but their identity is.** A managed-identity connection to
Service Bus, Storage or SQL works only when the app's identity holds the role on the target;
that grant is the pattern's wiring and the usual reason a workflow's first run fails after a clean
deployment. A connector that needs a consent flow (Office 365, SharePoint) is authorised by a
person after deployment and is said so in the handover.

**Log category names are the platform's.** `WorkflowRuntime` exists on both resource types; the
Standard site adds the web-site categories. Checked with
`az monitor diagnostic-settings categories list --resource <id>` before a render.

## Not covered here, and why

Integration accounts (B2B, EDI, maps and schemas), the Integration Service Environment (retired),
an App Service Environment for a Standard plan, deployment slots, custom domains and
certificates, hybrid connections and the on-premises data gateway each carry decisions of their
own and have no question set; a request for one is said out loud, not improvised.
