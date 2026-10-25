# API Management - what the question set cannot express

## Fixed at creation

- **The tier family.** Classic (Developer, Basic, Standard, Premium) and v2 (BasicV2,
  StandardV2, PremiumV2) are different platforms; moving between them is a migration into a new
  instance, not an edit. Consumption is a third.
- **The network mode.** Switching between `None` and an injected mode takes a long update (tens
  of minutes on the classic tiers) and can fail half-way; treat it as a re-create.
- **The name.** Global, 1-50 characters, letters, digits and hyphens, must start with a letter;
  it is the hostname (`<name>.azure-api.net`). It cannot be reused for 48 hours after a
  soft-delete unless the deleted instance is purged.
- **The region.**

## Ordering

Identity, key vault (named values and certificates), the subnet with its network security group
and route table, the public IP (classic injection), the instance - **thirty to ninety minutes on
the classic tiers**, minutes on the v2 tiers - then the APIs, the policy, the role assignments of
the instance's identity on the backends, then the consumers. The workspace before the diagnostic
setting.

## Pitfalls

**The modules disagree on the tier and its size.** Terraform defaults to `Developer_1`, Bicep to
`Premium` with three units. A Bicep render that leaves the default deploys the most expensive
tier. Every decision is written on the call.

**Developer is not a smaller production.** It has no SLA, one unit and a single node. A
`production` stage on `Developer` is a finding, not a saving: `sku` is derived from the outage
answer so that production never lands there silently.

**Injection needs a subnet of its own and the management rules.** A classic injected instance
needs inbound access to its management endpoint (port 3443) from the `ApiManagement` service
tag, outbound to Storage, SQL, Key Vault and Azure Monitor, and a Standard public IP - even for
an `internal` instance. A network security group that forgets the management rule fails the
deployment after the long wait. The v2 tiers take a delegated subnet and a different rule set.
Which tier supports which of private endpoint, VNet injection and VNet integration changes with
the product; read it from the documentation before a render.

**`internal` is reachable from the network only.** The gateway has a private address in the
subnet and no public DNS record: callers need a private DNS zone (`azure-api.net` or the custom
domain) that the platform owns. A pattern wires it; without it nothing resolves.

**The developer portal is a second public surface.** Even with the gateway `internal` the
portal can be public. It needs its own decision (`developer_portal`), a sign-in and a CORS
policy.

**A policy is code with a deploy pace of its own.** The global policy renders from two
decisions; an API team will edit it. The render owns the base and the API team's repository
owns the per-API policies, or the next deployment overwrites their work. Say which in the
handover.

**Keys are secrets the template does not hold.** With `subscription_key` the keys are created by
the service and read by the consumers; no key is rendered. Named values that hold secrets are
Key Vault references resolved by the instance's identity, which needs `Key Vault Secrets User`
first - the reason `user_assigned` exists for this resource.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <instance id>` before a render.

## Not covered here, and why

Self-hosted gateways, workspaces and federated APIs, custom domains and their certificates,
OAuth/OpenID authorisation servers, backends with circuit breakers, caches, MCP and
language-model gateway policies, and the import of API definitions each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
