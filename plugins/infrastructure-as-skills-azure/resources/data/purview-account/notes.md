# Microsoft Purview account - what the question set cannot express

## Fixed at creation

- **The account name.** Global, 3-63 characters, part of the portal URL and of every private
  endpoint's DNS name. A rename is a new account and a lost data map.
- **The region.** The data map's metadata cannot be moved; the account is created in one of the
  regions that offer Purview, which is not every Azure region.
- **The managed resource group name.** Set at creation; the group is created and deleted with the
  account.
- **The system-assigned identity.** Mandatory; an account cannot be created without it or have it
  removed.

## Ordering

The decision whether to create at all comes first: `ownership: platform` is the answer for every
deployment that is not the governance team's, and it renders a reference and nothing else. For
`deployment`: the account (which creates its managed group, storage account and, if enabled, the
Event Hubs namespace), then the `account` and `portal` private endpoints on the account, then the
`blob` and `queue` endpoints on the **managed** storage account - its id is an output of the
account, so they cannot be planned before it exists - and `namespace` on the managed namespace,
then the diagnostic setting and the role assignments, then the collection roles through the
account's data plane, then the sources register with it (a Data Factory's `purview_account`, a
scan of a lake). A closed ingestion path (`managed_resources_public_access: disabled`) also needs
a self-hosted integration runtime before the first scan.

## Pitfalls

**One account per tenant.** A second account splits lineage and doubles a fixed cost that is
already considerable (the data map's capacity units, the managed storage, the Event Hubs
namespace when on). The default is to reference; creating is the governance team's decision.

**Two permission systems.** Azure RBAC on the account is the control plane; who may see, curate or
register anything is a collection role inside the account, granted through the data plane. An
Azure `Owner` sees an empty portal. The creating principal becomes the first Collection admin,
which is why a service principal that deploys the account must hand the root collection to a
group before anyone else can work.

**Two halves of a private account.** `public_network_access: disabled` closes the front door
(`account`, `portal`); `managed_resources_public_access: disabled` closes the ingestion path
(`blob`, `queue`, `namespace`). The second needs the ingestion endpoints and a self-hosted
integration runtime for every scan, because the Azure-hosted runtime cannot reach a closed
ingestion path. Five private DNS zones in all.

**The managed Event Hubs namespace is billed around the clock.** Both the Bicep module and the
azurerm resource default it on; the question defaults it off, and the `namespace` endpoint exists
only with it on.

**The Terraform side is authored.** The AVM Terraform module is `Proposed` in the index and not
published; the render uses `azurerm_purview_account` on 5.x, which has no argument for the managed
resources' public access (an `azapi_update_resource` sets it), no private endpoints, no diagnostic
setting and no role assignments of its own - each is an authored resource beside it. The Bicep
module carries all of them, with one parameter per endpoint kind.

**Diagnostic categories carry export cost.** `DataSensitivityLogEvent` and `Security` are billed
per gigabyte exported; their volume follows the number of scanned assets.

**No customer-managed key.** The account does not support one; `key_management: customer_managed`
in the deployment does not reach this resource and the handover says so.

## Not covered here, and why

Collections, classifications, glossaries, scans, source registrations and policies (the data
plane, the programme's pace), the self-hosted integration runtime's machine (compute family),
Purview's Microsoft 365 compliance and data security solutions (licensed per user, not an Azure
resource), and a customer-managed key (unsupported) each carry decisions of their own or belong
elsewhere; a request for one is said out loud, not improvised.
