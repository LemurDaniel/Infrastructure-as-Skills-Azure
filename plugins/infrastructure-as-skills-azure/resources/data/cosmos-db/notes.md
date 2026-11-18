# Cosmos DB - what the question set cannot express

## Fixed at creation

- **The partition key of a container.** It cannot be changed; a different key is a new
  container and a data migration. It decides cost and throttling more than anything else.
- **The capacity mode** (provisioned or serverless). An account is migrated, not converted.
- **The free-tier flag.** One account per subscription; an account without it never gets it.
- **Zone redundancy of a region.** Set when the region is added; to change it a region is added
  and the old one removed.
- **A customer-managed key.** Set at creation, cannot be removed; losing the key makes the
  account unreadable.
- **Analytical storage.** Enabling and then disabling it forces a new account.
- **The name.** Global, lowercase, 3-44 characters, part of the endpoint
  `<name>.documents.azure.com`.

## Ordering

The identity and its role on the Key Vault key (when `key_management: customer_managed`),
then the account, then databases and containers, then the data-plane role assignments (they
need the account and the database or container as scope), then the consumers. The workspace
before the diagnostic setting.

## Roles

**Cosmos DB's data access is its own role system**, separate from Azure RBAC: `Cosmos DB
Built-in Data Reader` and `Cosmos DB Built-in Data Contributor` are assigned on the account
with `sqlRoleAssignments`, and an Azure `Contributor` or `Owner` role does not read a single
item. Both kinds are `wiring.role_assignments` entries with the account as `to`; the role's
name says which model it belongs to (`data_plane` in built-in-roles.yaml), and the render
writes it accordingly.

With local authentication off, nothing reads the data until a data role is assigned, so an
account without one for its caller works and is of no use to anyone. A consumer nobody has
named is an `open:` entry (key `wiring.role_assignments`) owned by the workload owner,
blocking apply. The scope of an entry is the account - a database or a container is a part
of it, no resource of the spec.

An Azure RBAC role on the account is the control plane - creating databases, changing
throughput, reading keys if they were enabled - kept apart from the data roles on purpose.
Usually the deploying principal holds these alone, and the spec then has no entry for it.

## Pitfalls

**Two permission systems.** Azure RBAC governs the control plane; the data plane has its own
roles (`Cosmos DB Built-in Data Reader`, `Built-in Data Contributor`) assigned on the account
itself. With local authentication off, nothing reads an item until a data-plane role is
assigned - an Azure `Owner` does not. The **Terraform AVM module has no input** for them: they
are rendered next to the module.

**A closed account cannot be filled from outside the network.** With
`public_network_access: disabled` the data plane is reachable only through the private
endpoint. A runner outside the network creates the account (control plane) and then cannot
create databases or containers through the data plane where the module does so by key. Both
modules create databases and containers through Azure Resource Manager, so this holds for
the template and bites a seeding script instead.

**Throttling is the failure, and it is silent in the portal.** A request over the throughput
returns 429; the SDKs retry, so the symptom is latency. The partition key, not the account
ceiling, is usually what throttles: throughput is divided evenly over physical partitions.

**Autoscale is per container or database, not per account.** `total_throughput_limit` is the
account-wide guard.

**The modules disagree on defaults.** Consistency (`BoundedStaleness` in Terraform,
`Session` in Bicep), periodic backup redundancy (`Geo` versus `Local`) and burst capacity
(false versus true) differ; every decision is written on the call.

**Continuous backup excludes multi-region writes**, and periodic to continuous is one-way.

**The query log carries query text.** `QueryRuntimeStatistics` can hold personal data; it is
a recorded choice.

**Log category names are the platform's.** Checked against `az monitor diagnostic-settings
categories list --resource <account id>` before a render.

## Not covered here, and why

Other APIs (MongoDB, Cassandra, Gremlin, Table), multi-region writes, the dedicated gateway,
Synapse Link, indexing policies, vector and full-text policies, stored procedures, triggers,
and a hierarchical partition key each carry decisions of their own and have no question set; a
request for one is said out loud, not improvised.
