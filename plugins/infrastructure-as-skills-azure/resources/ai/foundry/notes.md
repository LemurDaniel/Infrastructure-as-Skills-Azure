# AI Foundry - what the question set cannot express

## Fixed at creation

- **The kind** (`AIServices`, `OpenAI`) and the **custom subdomain**. The subdomain is the
  account's hostname, must be globally unique, and is required for token authentication,
  a firewall and private endpoints; it cannot be changed.
- **The name.** Part of the subdomain and the endpoint.
- **A deployment's model name** and tier-shaped scale fields. A different model is a new
  deployment; a deployment name is what the application calls, so renaming it is a breaking
  change for every caller.
- **The region.** It decides which models, versions and quota exist.

## Ordering

The identity and its role on the Key Vault key (when `key_management: customer_managed`),
then the account, then the model deployments (one after another: the AVM Terraform module
serialises them by default, because parallel creation returns `409 Conflict`), then the
projects, then the role assignments, then the connections from the projects to storage, search
and Cosmos DB - which are the pattern's wiring. The workspace before the diagnostic setting.

## Pitfalls

**Quota is the failure, and it is not in the template.** A model deployment counts against a
per-subscription, per-region, per-model quota. A deployment that exceeds it fails at apply
with a quota error; the fix is a quota request to Microsoft, or a different region or
deployment type. Two deployments of one model in one subscription share it.

**The model list is regional and short-lived.** A model, a version and a deployment type are
offered per region and retired on a schedule. A version pinned in a spec expires; the
`version_upgrade_option` decides whether that is an upgrade or an outage.

**A Foundry account in another region keeps its endpoint at home.** When the account departs
from `context.location` (`placement.location`), the private endpoint still sits in the
network's subnet and region - a private endpoint reaches a resource in any region. The
Terraform module places the endpoint in the *account's* region unless the entry names one, so
the render writes it; Bicep takes the network's. The resource group, the workspace and the
connected storage and search stay where they are; diagnostics and calls cross the region,
which costs latency and a little egress, not a design change. Agent network injection is the
exception: it requires the account in the network's region.

**`GlobalStandard` is the portal's default and processes anywhere.** `DataZoneStandard` keeps
processing in the data zone. For a mandate that names residency this is the decision that
matters, and it is easy to take by clicking through.

**Private access needs three DNS zones.** An AI Services account answers under
`cognitiveservices`, `openai` and `services.ai` hostnames. The platform's private DNS zones
must cover all three, or the first call to the missing one fails name resolution.

**Keys off means roles on.** A caller needs `Cognitive Services OpenAI User` (models only) or
`Azure AI User` (projects and agents) and a token for the account's custom subdomain. The
playground in the portal reaches a closed account only from inside the network.

**Outbound restriction breaks tools.** `restrict_outbound: true` stops the account calling any
address that is not in `allowed_fqdns`; an agent tool that calls a public API fails at the call,
not at the deployment, until its host name is added to the list.

**Projects are not created by either module.** They are rendered as child resources next to
the module, each with an identity whose roles are the pattern's wiring.

**The modules disagree on defaults.** Local authentication (Terraform on, Bicep off), outbound
restriction (Terraform off, Bicep on), the deployment upgrade option and public access differ;
every decision is written on the call.

**Log category names are the platform's** and differ between `OpenAI` and `AIServices`
accounts: checked against `az monitor diagnostic-settings categories list --resource <account
id>` before a render.

## Not covered here, and why

Agents, prompt flows, evaluations, fine-tuning, custom content-filter policies, commitment
(reserved) plans, provisioned throughput deployments, other Cognitive Services kinds, and the
Azure Machine Learning hub have no question set; a request for one is said out loud, not
improvised.
