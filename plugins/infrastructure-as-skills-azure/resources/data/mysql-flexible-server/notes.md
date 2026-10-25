# MySQL Flexible Server - what the question set cannot express

## Fixed at creation

- **The server name.** Global, lowercase, 3-63 characters, part of the endpoint
  `<name>.mysql.database.azure.com`.
- **The network mode.** Public access (with private endpoints) and VNet integration cannot be exchanged; the
  documented way is a point-in-time restore into a new server.
- **Geo-redundant backup.** Chosen at creation.
- **A customer-managed key.** Set at creation; cannot be removed.
- **Storage never shrinks.**
- **A custom port**, if one is used, cannot be updated afterwards.

## Ordering

The user-assigned identity first (it is needed for Entra authentication, and for a customer-managed key
together with its role on the Key Vault key), then the server, then the Entra administrator (the module waits
for the identity; `active_directory_administrator_wait_seconds` lengthens the wait), then databases and server
parameters, then the `database_users` step (SQL, as a member of the administrator group), then the consumers.
The workspace before the diagnostic setting.

## Pitfalls

**An administrator account is demanded even for Entra-only.** MySQL requires `administrator_login` and a
password at creation; `aad_auth_only = ON` then turns password sign-in off. The password is generated for the
call - write-only in Terraform (needs Terraform 1.11), a secure parameter with a generated default in Bicep -
and is never stored, output or used.

**Entra authentication needs a user-assigned identity with Graph permissions.** The identity reads the
directory for the server; it needs `User.Read.All`, `GroupMember.Read.All` and `Application.Read.All`, a
tenant decision the platform owns. A system-assigned identity does not work, which is why there is no
`managed_identity` choice here.

**Two permission systems.** Azure RBAC governs the server; inside it, accounts and grants are SQL. With
password authentication off, nothing reads a row until `CREATE AADUSER` has run. No ARM resource does it, so
the plugin records `database_users` and names the step.

**`tls_version` is a list, not a minimum.** The parameter takes `TLSv1.2,TLSv1.3`; "at least 1.2" renders as
both.

**Both modules default geo-redundant backup on** (and the Bicep module defaults the MySQL version to 8.0.21 and
storage auto-grow to disabled); every decision is written on the call.

**8.0 is leaving support.** Community support for 8.0 ends in 2026; the default is 8.4. A major upgrade is in
place and one-way.

**The slow log carries statement text** and is written only once `slow_query_log` is on; both are off the
question set.

**Private endpoint versus VNet integration.** A private endpoint works on a public-access server whose public
access is then switched off; a VNet-integrated server has no private endpoint at all. The current documentation
is checked before a render.

**Defender for open-source relational databases is a subscription plan.** The server setting binds the server to
it; the plan itself is the platform's.

## Not covered here, and why

Read replicas, data-in replication, import from Single Server, custom ports, geo-replicas (recorded as an open
entry for `critical`), and tuning of server parameters beyond the ones named each carry decisions of their own
and have no question set; a request for one is said out loud, not improvised.
