# Communication Services - what the question set cannot express

## Fixed at creation

- **The data location.** Both resources; a different geography is a new resource, with new
  phone numbers, a new endpoint and a new domain link.
- **The domain management kind** (Azure-managed or customer-managed) and the domain name.
- **The name.** Global; it is the endpoint hostname (`<name>.<region-independent>.communication.azure.com`).

## Ordering

The e-mail service, its domain, the sender usernames; for a custom domain the verification
records in the organisation's DNS (Domain TXT, SPF, DKIM, DKIM2, DMARC - read from the domain
resource after the first apply) and the verification itself, which is a portal or CLI action
and not a template property; then the communication service with the domain linked, then the
role of the application's identity, then the diagnostic setting (workspace before it). Phone
numbers and Teams interoperability are purchases after everything else.

## Pitfalls

**There is no private endpoint.** The resource has `publicNetworkAccess`, but `Disabled` without
a network security perimeter association leaves nothing able to call it, including the
application. The honest private posture is `Enabled` with `disableLocalAuth` and roles; the set
records that as forced, and a platform that has a perimeter lifts it to `SecuredByPerimeter`.

**The API version decides which switches exist.** `disableLocalAuth` and `publicNetworkAccess`
arrived with `2025-09-01` (the version the Bicep module targets); an older `apiVersion` - or the
`azurerm_communication_service` resource, which exposes neither - silently leaves both at the
platform default (keys on, public). The Terraform render uses `azapi` for the resource for this
reason.

**Domain verification is a person's job.** A customer-managed domain is created unverified. The
TXT, SPF, DKIM and DMARC records come out of the deployed domain resource and go into a zone this
set does not own; the domain sends nothing until the verification is triggered and succeeds. The
handover carries the records and names the owner.

**The Azure-managed domain is a test domain.** `DoNotReply@<guid>.azurecomm.net` sends
immediately, with a low daily limit and from an address no recipient recognises; it is right for
a development stage and for internal notifications, wrong for customer mail.

**The link is to the domain, not the service.** `linkedDomains` takes domain resource ids
(`.../emailServices/<name>/domains/<domain>`); a service id is rejected at apply.

**Keys off changes the SDK call, not the endpoint.** With `disableLocalAuth` the application
constructs its client with a token credential and the endpoint, holds `Communication and Email
Service Owner` (or the narrower role the SDK documents for its operation), and the
user-identity and token APIs keep working - the tokens the resource issues for end users are not
access keys.

**Log category names are the platform's and move per channel.** Checked against
`az monitor diagnostic-settings categories list --resource <id>` before a render; the e-mail
categories exist only once the e-mail channel has been used.

## Not covered here, and why

Phone numbers, short codes and alphanumeric sender IDs, Teams interoperability and Teams Phone
extensibility, call recording storage (a storage account with a role for the resource's
identity - a pattern), network security perimeters, advanced messaging (WhatsApp) channel
registrations and the customer-managed-key story (the service encrypts with platform keys)
have no question set; a request for one is said out loud, not improvised.
