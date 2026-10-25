# PostgreSQL Flexible Server - what the question set cannot express

## Fixed at creation

- **The server name.** Global, lowercase, 3-63 characters, part of the endpoint
  `<name>.postgres.database.azure.com`.
- **The network mode.** A server created with VNet integration cannot take a private endpoint, and a
  public-access server cannot become VNet-integrated; either move is a restore into a new server.
- **Geo-redundant backup.** Chosen at creation.
- **A customer-managed key.** Set at creation; cannot be removed, and losing the key makes the server
  inaccessible.
- **Storage never shrinks.** Growth is in place, reduction is a dump and a new server.
- **A database's character set and collation.**

## Ordering

The identity and its role on the Key Vault key (when `key_management: customer_managed`), then the server, then its
Entra administrators (the module orders them), then databases and configurations, then the `database_roles`
step (SQL, as a member of the administrator group), then the consumers. For VNet integration the delegated
subnet and the private DNS zone link come first. The workspace before the diagnostic setting.

## Pitfalls

**Two permission systems.** Azure RBAC governs the server; inside it, roles are SQL. With password
authentication off, nothing reads a row until an Entra role is created (`pgaadauth_create_principal`) - an
Azure `Owner` does not. No ARM resource does it, so the plugin records `database_roles` and names the step.

**The Terraform module's default firewall admits every address.** `firewall_rules` defaults to a rule from
`0.0.0.0` to `255.255.255.255`; it is written, empty, on every call.

**The modules disagree on defaults.** Geo-redundant backup (the provider's `false` in Terraform, `Enabled` in
Bicep), the maintenance window (00:00 versus 01:00), the PostgreSQL version (the module's description ends at 16
in Terraform, the Bicep default is 18), and the authentication block (null versus Entra-only); every decision is
written on the call.

**Burstable has no high availability.** The Terraform module's `high_availability` default is `ZoneRedundant`,
which a burstable size refuses; the render sets `null` for it.

**Extensions are an allow-list.** An extension is usable only after `azure.extensions` names it and
`shared_preload_libraries` loads it where required, both server parameters; a server restart follows the
second. Not rendered here.

**A closed server cannot be reached from outside the network.** With `public_network_access: disabled` the SQL
step runs from a runner inside the network.

**The server log carries statement text.** `PostgreSQLLogs` can hold personal data in slow statements; the
slow-statement threshold is a server parameter, off the question set.

**Defender for open-source relational databases is a subscription plan.** The server setting binds the server to
it; the plan itself is the platform's.

**Backups outside the server.** The platform keeps the automated backups outside the server, so
`backup_isolation: isolated` is met by default for the retention window; an isolated or immutable copy beyond
it is the Backup vault (the `backup-vault` family lists PostgreSQL) and a pattern adds it - whether the vault
covers a *flexible* server is checked against its current documentation before it is claimed.

## Not covered here, and why

Read replicas and virtual endpoints, geo-replicas (recorded as an open entry for `critical`), major-version
upgrades, PgBouncer tuning, pgAudit, extensions, logical replication, Single Server and Cosmos DB for PostgreSQL
each carry decisions of their own and have no question set; a request for one is said out loud, not improvised.
