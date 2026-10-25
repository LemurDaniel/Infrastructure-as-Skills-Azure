# Front Door - what the question set cannot express

## Fixed at creation

- **The tier, in part.** Standard to Premium is possible in place; Premium to Standard is not.
- **The profile name** (within the resource group) and, once created, the endpoint host name,
  whose hash is generated.
- **A custom domain's association** to an endpoint: moving a domain between profiles needs the
  old association removed first, and the DNS validation record repeated.

## Ordering

Resource group, identity and Key Vault certificate (customer certificates only), the WAF policy,
the profile, the endpoint, origin groups and origins, **the origin owner's approval of each
private-link connection**, routes, custom domains, the security policy that binds the firewall
to the endpoint and domains, then the DNS records. The workspace before the diagnostic setting.

## Pitfalls

**A private origin is pending until someone approves it.** `origin_connection: private_link`
creates a private endpoint connection on the *origin*, in state *Pending*. Until its owner
approves it, the origin is unreachable and the health probe fails. The approval is a step outside
the template (a role on the origin, `az network private-endpoint-connection approve`), an
`open:` entry owned by the origin's owner.

**A public origin must lock itself to Front Door.** Without private link the backend is reachable
by anyone who knows its address. Admit only the `AzureFrontDoor.Backend` service tag and check the
`X-Azure-FDID` header against the profile's id, or the firewall is bypassed by calling the backend
directly.

**The firewall policy and the profile must be the same tier.** A Premium policy cannot attach to a
Standard profile, and managed rule sets exist only on Premium. A `Standard` profile with
`waf_managed_rules: true` is forced to Premium rather than failing late.

**Detection is not protection.** A firewall left in `Detection` records attacks and lets them
through; moving there is a temporary, owned departure.

**Caching personal responses leaks them.** Cache static routes only; the cache key must include
anything that varies the response. `caching` defaults to off.

**A global service cannot keep data in a country.** Requests are terminated and cached at edge
locations around the world; `data_residency: country` cannot be met by Front Door and, with
`data_zone`, the edge locations are still not limited to the zone. Where residency is a hard
requirement the answer is a regional Application Gateway, not Front Door, or an explicit,
recorded acceptance by the data owner. The decision document says so rather than hiding it.

**Managed certificates need the DNS proof.** The validation TXT record is created by the DNS owner
before the certificate issues; a domain that never validates stays in *Pending* and serves the
default certificate. A customer certificate expires without notice unless someone owns its renewal.

**Timeouts differ between the modules** (120 s in Terraform, 60 s in Bicep). Every value is
written on the call.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <profile id>` before a render.

## Not covered here, and why

Classic CDN (Microsoft, Verizon, Akamai, the China SKUs), the retired Front Door classic, rule
sets (URL rewrites, header actions, redirects beyond HTTP to HTTPS), origin groups with weighted
or latency-based routing, session affinity, and private-link approval automation each carry
decisions of their own and have no question set; a request for one is said out loud, not
improvised.
