# Azure SQL Database - what the question set cannot express

## Fixed at creation

- **The server name.** Global, lowercase, 1-63 characters, part of the endpoint
  `<name>.database.windows.net`. A rename is a new server.
- **A database's collation.** Cannot be changed; a different one is a new database and a data move.
- **The backup storage redundancy of a database.** Chosen at creation (`Local`, `Zone`, `Geo`,
  `GeoZone`); changing it later is a copy into a new database.
- **The purchasing model.** The vCore model is rendered; DTU databases are not offered, and a move
  between the two is a scale operation with its own limits.
- **Hyperscale.** Moving to it is practically one-way; a return is possible only for a short window.
- **Administrator login.** With SQL authentication in use the login name cannot change; with Entra-only it is
  not rendered at all.

## Ordering

The identity (and its role on the Key Vault key when `key_management: customer_managed`), then the
server with its Entra administrator, then the databases and pools, then the server audit policy and the
diagnostic setting on `master`, then the `database_users` step (T-SQL, as a member of the administrator
group), then the consumers. The workspace before every diagnostic setting.

## Pitfalls

**Two permission systems.** Azure RBAC governs the control plane; inside each database the roles
(`db_datareader`, `db_datawriter`) are T-SQL. With SQL authentication off, nothing reads a row until a
user is created from the Entra identity - an Azure `Owner` does not. No ARM resource creates a database
user, so the plugin records `database_users` and names the step.

**The server identity needs directory rights.** `CREATE USER ... FROM EXTERNAL PROVIDER` for a group
or an application resolves it through the server's identity, which needs the `Directory Readers` role (or
the Graph application permissions). That is a tenant decision the platform owns; without it the user step
fails with a resolution error.

**A closed server cannot be reached from outside the network.** With `public_network_access: disabled` the
T-SQL step runs from a runner inside the network, or through a deployment script in it.

**Auditing needs two settings.** The server audit policy with an Azure Monitor target, and a
diagnostic setting on `master` for `SQLSecurityAuditEvents`. Either alone records nothing. The Terraform
module renders neither; the Bicep module renders the first.

**Defender for SQL is a subscription plan.** The server-level policy (`threat_detection`) binds the server to it;
the plan itself is the platform's, and an alert needs both.

**"Allow Azure services" is any tenant's Azure.** The `0.0.0.0` rule admits every resource in Azure, not this
customer's. It is a decision with its own question, off by default.

**The modules disagree on defaults.** Backup storage (`Geo` in the Terraform module), the audit setting
(enabled, with no destination, in the Bicep module), the elastic pool's zone redundancy (`true` in
Terraform); every decision is written on the call.

**The Terraform module fixes TLS at 1.2** and builds no audit and no server-level alert policy; the Bicep
module accepts 1.3. A stricter answer than the floor forces the authored server on Terraform.

**A database metric category is `Basic`**, not `AllMetrics`; the module's default for the latter fails the plan.

**Serverless pauses.** The first connection after a pause pays a cold start of up to a minute and some
drivers' default timeouts are shorter; the retry policy is the application's.

## Not covered here, and why

SQL Managed Instance, SQL on a VM, Synapse dedicated pools, failover groups and geo-secondaries (the second
region is recorded as an open entry), long-term-retention immutability, ledger, Always Encrypted with
enclaves, elastic jobs, import and restore create modes, and the DTU model each carry decisions of their own
and have no question set; a request for one is said out loud, not improvised.
