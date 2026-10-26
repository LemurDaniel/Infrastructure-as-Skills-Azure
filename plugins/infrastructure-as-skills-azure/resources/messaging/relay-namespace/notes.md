# Azure Relay namespace - what the question set cannot express

## Fixed at creation

- **The name.** Global, 6-50 characters, starts with a letter, ends with a letter or digit; it is
  the hostname (`<name>.servicebus.windows.net`, the suffix shared with Service Bus and Event
  Hubs). The Terraform module refuses a shorter one at plan time.
- **The region.**
- **The tier.** Standard is the only one; there is nothing to choose or to change.

## Ordering

The namespace, then the network rule set (Terraform: a submodule after the namespace; Bicep: a
child the module orders), then the hybrid connections and WCF relays, then the role assignments
of the listeners and senders **on each connection**, then the far side: the listener process or
the App Service hybrid-connection binding, which needs the connection to exist. The workspace
before the diagnostic setting.

## Pitfalls

**Relay is a rendezvous, not a network.** Both sides open outbound 443 to the namespace; the
relay joins them. Nothing becomes routable, no address space is shared, and a listener that
goes away takes the connection with it. A request for "reach the on-premises network" with
many services and both directions is a VPN or ExpressRoute; a relay is for one service, one
port, outbound-only on the far side.

**The namespace has no key switch.** `RootManageSharedAccessKey` is created by the service with
every namespace and cannot be removed; nothing in the API turns SAS off. `local_auth: disabled`
is therefore recorded as `forced` and kept as a convention: no rule rendered (Bicep
`authorizationRules: []`, no `authorization-rule` submodule in Terraform), no `listKeys`, no
connection string in a setting; listeners hold `Azure Relay Listener` and senders `Azure Relay
Sender` on the hybrid connection. The right to list the root key is the control-plane role
assignment on the namespace, which is why `Azure Relay Owner` and `Contributor` are for the
deploying principal only.

**An on-premises listener needs an identity too.** Entra ID on the far side is a service
principal with a certificate or a managed identity through Azure Arc; the Hybrid Connection
Manager beside an App Service uses the web app's binding. A listener with neither is the one
legitimate SAS case: a `Listen`-only rule on that single connection, recorded as a departure
and an `open:` entry, never the root rule.

**WCF relays are SAS-only.** They predate Entra ID on the data plane and have no identity path.
Each entry in `wcf_relays` is a departure in itself; a WCF service that can be fronted by a
hybrid connection should be.

**The two modules carry the children differently.** The Bicep module takes `hybridConnections`,
`wcfRelays`, `authorizationRules` and `networkRuleSets` as parameters of one call and defaults
`authorizationRules` to the root rule; the Terraform root module has none of them and ships
`hybrid-connection`, `wcf-relay`, `authorization-rule` and `network-rule-set` as submodules
called beside it. The Terraform root writes `publicNetworkAccess` on the namespace, the Bicep
module only through the `networkRuleSets` child; both are written.

**`disabled` means no firewall at all.** With public access off the service ignores the rule
set, and the modules write `null` for the rules. The allowlist exists only under
`enabled_with_firewall`, and a listener outside Azure must be in it or nothing connects.

**Nothing to size, nothing to harden beyond the above.** No capacity, no zones, no managed
identity, no customer-managed key, no TLS floor setting: the type exposes none. A spec that
asks for them records *not applicable on this resource*, not *done*.

**Log category names are the platform's.** They are checked against
`az monitor diagnostic-settings categories list --resource <namespace id>` before a render.
Both categories land in the shared `AzureDiagnostics` table, so the workspace query filters on
`ResourceType == "NAMESPACES"` and `Category`.

## Not covered here, and why

The listener itself (the Hybrid Connection Manager, a custom listener process, the Azure Arc
onboarding of an on-premises host), the App Service side of a hybrid connection
(`Microsoft.Web/sites/hybridConnectionNamespaces/relays`, the web app's set), per-connection
authorization rules for the SAS departure, and the `SecuredByPerimeter` network mode each carry
decisions of their own and belong elsewhere or have no question set; a request for one is said
out loud, not improvised.
