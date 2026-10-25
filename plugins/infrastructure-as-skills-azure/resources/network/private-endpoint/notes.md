# Private endpoint (standalone) - what the question set cannot express

## When this set is used, and when it is not

Almost every resource set already renders its private endpoints, through the AVM module's
shared interface (`private_endpoints` / `privateEndpoints`), from its own
`private_endpoint_subnet` and `private_endpoint_subresources` questions. **Use that, not this.**
This set exists for three cases:

| Case | Why the resource's own set does not apply |
|---|---|
| The target is **not created here** - an existing Key Vault, another team's storage account | No module call to attach the interface to |
| The target's module **does not carry** the interface (or the set has not been written) | Nothing to render it through |
| The target is a **Private Link service** (`Microsoft.Network/privateLinkServices`) of another team | A manual connection to something this deployment does not own |

The decisions it inherits are not re-asked: the subnet (`deployment.private_endpoint_subnet`),
who owns the DNS zones (`private_dns_ownership`), who writes the records (`private_dns_records`)
and the zone scope (`private_dns_zone_scope`). The table of which zone belongs to which
sub-resource is [private-dns-zones.md](../../../core/iac-rendering/references/private-dns-zones.md),
shared with every set that has an endpoint.

## Fixed at creation

- **The target and the sub-resource.** An endpoint is bound to one resource and one group id;
  another target or another group id is a new endpoint.
- **The subnet.** Moving an endpoint to another subnet recreates it, and its address changes.
- **The network interface name and the connection name** - a change forces a new endpoint.
- **The region** - that of the subnet's network, not the target's.

## Ordering

1. The target, and the network with its endpoint subnet
2. The private DNS zone and its link to the network, where this deployment creates them
3. The private endpoint - last, because it takes an address from the subnet and needs the zone
   to attach to
4. The target's `public_network_access: Disabled` - only after the endpoint resolves, or the
   deployment cuts itself off from the target

Deletion runs the other way. The subnet holding an endpoint refuses to go and names the
endpoint; `terraform destroy` on a network with endpoints from another configuration in it is
the common version of this.

## Pitfalls

**Two writers for one record.** An endpoint with a zone group, in a landing zone whose
DeployIfNotExists policy also writes the record, is a plan that shows drift on every run and a
policy that re-applies what the code removed. `dns_zone_group: left_to_policy` renders no zone
group at all; that is what the platform default asks for.

**No zone group, no policy: nothing resolves.** The opposite failure: the endpoint exists, the
name resolves to the target's public address, and the traffic works while leaving the private
path unnoticed. The name resolves to the public address whenever no privatelink record is
returned - check from a machine in the network, not from the pipeline.

**Custom DNS servers need the zone forwarded.** If the network's `dns_servers` are not Azure's
(virtual-network set), the privatelink zones must be forwarded to Azure DNS (168.63.129.16), or
the same symptom appears with every record in place.

**One endpoint, one group id.** A storage account used for blobs and files is two endpoints and
two zones. `foundry` is one endpoint (`account`) and three zones.

**The group id is case-sensitive and per target type.** `Sql` for Cosmos DB's NoSQL API,
`sites` for App Service, `registry` for a container registry, `namespace` for Service Bus and
Event Hubs. The table in `private-dns-zones.md` is the list; a guess from the portal's label
is rejected at apply with a message that names the allowed values.

**A manual connection is created `Pending`.** Nothing resolves and nothing connects until the
target's owner approves it. That is a handover step, not a deployment error.

**Network policies apply only when the subnet says so.** An NSG or a route on the endpoint
subnet takes effect for endpoint traffic only with `private_endpoint_network_policies: Enabled`
on the subnet (virtual-network set). A UDR to a firewall on that subnet then sends endpoint
traffic through the firewall, which has to allow and route the replies back symmetrically.

**Static addresses are bound to the group id.** A fixed address is set per sub-resource and
member name; a typo in either is rejected at apply.

## Not covered here, and why

Application security groups on the endpoint, custom DNS configurations, endpoints over several
group ids, and private link services of this deployment's own each carry decisions of their own;
none has a question set. A request for one is said out loud, not improvised.
