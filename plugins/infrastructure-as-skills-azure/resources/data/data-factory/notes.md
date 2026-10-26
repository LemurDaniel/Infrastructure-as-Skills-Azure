# Azure Data Factory - what the question set cannot express

## Fixed at creation

- **The factory name.** Global, 3-63 characters; a rename is a new factory and a re-publish of
  the content.
- **The customer-managed key.** Set when the factory is created; an existing factory cannot be
  moved to one.
- **The managed virtual network** can be switched on later, never off; the Azure integration
  runtime's `virtual_network_enabled` is fixed per runtime.
- **The git binding** can be removed and re-made, but the content in live mode and the content
  in the branch diverge the moment they differ - bind the development factory before anyone
  authors in it.

## Ordering

The user-assigned identity and its role on the Key Vault key when `key_management:
customer_managed`, then the factory with its managed virtual network, then the Azure integration
runtime inside it, then the managed private endpoints - each of which the **source's owner
approves** before a linked service can use it (a deployment script or the pipeline approves the
connection where this deployment owns the source) - then the private endpoints (`dataFactory`,
`portal`), the diagnostic setting, the role assignments on the sources (`source_access`), and
last the content through the factory's own CI/CD. A GitHub binding needs one interactive sign-in
in the authoring portal after the deployment; Azure DevOps binds with the tenant alone.

## Pitfalls

**Infrastructure and content are two deployments.** This set renders the factory; the pipelines,
datasets, linked services, data flows and triggers are published from the development factory's
repository by the ARM template the factory generates (`adf_publish`, or the npm publish package).
Rendering a linked service here means it is overwritten at the next publish - or it overwrites a
change the authors made. Global parameters are the exception and the content pipeline must be told
to leave them alone.

**One factory per stage, git on the development one only.** A production factory bound to git
turns every save into a deployment; a development factory in live mode has no review. `git_provider`
is per stage for that reason, and the other stages take `none`.

**The posture has two halves.** `public_network_access` closes the factory's own API and portal;
`managed_virtual_network` plus `managed_private_endpoints` is how the factory reaches sources that
are closed. One without the other is a factory nobody can open, or one that opens and copies
nothing: the sources refuse the shared runtime's public addresses.

**A closed factory needs the runner inside.** With the API behind a private endpoint, the content
pipeline's publish and `terraform apply` of anything that calls the factory API (the managed
private endpoints, the runtimes, in Terraform) run from a runner that resolves
`privatelink.datafactory.azure.net`.

**The modules disagree with each other and the guardrail.** Public access: the Terraform module
defaults to `true`, the Bicep module to disabled only when endpoints are passed. The managed
network: both off. Every decision is written on the call.

**The Terraform module carries less.** Its private endpoints are `dataFactory` only (the portal
endpoint is authored), it has no managed private endpoints and no Azure integration runtime input,
and its `integration_runtime_self_hosted` map asks for the factory id it creates. The Bicep module
carries all of them.

**The self-hosted runtime key is a secret.** It is read from the runtime after creation
(`listAuthKeys`) into the Key Vault, never into an output or a parameter file; the machine joins
with it, and the machine is the compute family's.

**Diagnostics are resource-specific.** `Dedicated` tables (`ADFPipelineRun`, `ADFActivityRun`);
`AzureDiagnostics` truncates activity output. Both modules default to `Dedicated`.

**Lineage needs a data-plane role.** A connected Purview account records lineage only when the
factory's identity holds `Data Curator` on the root collection - a Purview collection role, not
Azure RBAC.

## Not covered here, and why

The content (pipelines, datasets, data flows, linked services, triggers, credentials),
Azure-SSIS integration runtimes, Workflow Orchestration Manager (Airflow), the version 1 model,
Fabric Data Factory, the self-hosted runtime's machine, and the roles on the sources each carry
decisions of their own or belong to another set; a request for one is said out loud, not
improvised.
