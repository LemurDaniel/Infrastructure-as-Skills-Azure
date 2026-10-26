# Azure SQL Managed Instance - what the question set cannot express

## Fixed at creation

- **The instance name.** Global, lowercase, 1-63 characters, part of the host
  `<name>.<dnszone>.database.windows.net`. A rename is a new instance.
- **The collation and the time zone.** Instance-wide, set at creation, never changed; a different
  one is a new instance and a migration.
- **The backup storage redundancy.** `Local`, `Zone`, `Geo` or `GeoZone` is chosen at creation;
  changing it is a new instance.
- **The subnet.** The instance is injected into it; moving it is a scale operation as long as a
  new deployment. The subnet's delegation, NSG and route table must exist first.
- **The DNS zone partner.** A secondary instance for a failover group must be created with
  `dns_zone_partner` pointing at the primary; it cannot be added later.
- **The hardware generation** is changed only by a scale operation of several hours.

## Ordering

The subnet with its delegation, network security group and route table (the platform's or the
network set's), then the identity and its role on the Key Vault key when
`key_management: customer_managed`, then the instance with its Entra administrator - **four to six
hours** for a new instance in an empty subnet, around 90 minutes for a further instance in a
subnet that already holds one; every scale operation afterwards takes hours as well - then the
databases, the diagnostic settings, the threat-protection setting, then the T-SQL steps (the server
audit, the logins and `database_users`), then the consumers. The workspace before every
diagnostic setting.

Plan the pipeline around the duration: the deploy job's timeout and the Terraform `timeouts`
(the module's default is 24 hours) must cover it, and a failed first attempt costs the same time
again. A development stage that is torn down nightly is the wrong shape for this resource.

## Pitfalls

**The subnet is the deployment.** Too small a prefix (`/27` is the minimum, `/26` for a
production estate that will scale), a missing delegation, an NSG without the management rules the
service adds, a route table missing the `0.0.0.0/0` to `Internet` route the service injects, or a
forced tunnel without the service tags: each fails the deployment after a long wait. The subnet
holds nothing but managed instances.

**Two permission systems.** Azure RBAC governs the control plane; inside the instance the logins
and database roles are T-SQL. With SQL authentication off, nothing reads a row until a login is
created from the Entra identity - an Azure `Owner` does not. No ARM resource creates it; the
plugin records `database_users` and names the step, which runs from inside the network.

**The instance identity needs directory rights.** `CREATE LOGIN ... FROM EXTERNAL PROVIDER` for a
group or an application resolves it through the identity, which needs the `Directory Readers`
role (or the Graph application permissions). That is a tenant decision the platform owns; without
it the login step fails with a resolution error.

**Entra-only still needs a SQL administrator in Terraform.** The provider requires
`administrator_login` and a password; the render generates the password and never stores it, and
the login cannot sign in while `azuread_authentication_only_enabled` is on. The Bicep module takes
the Entra administrator alone.

**Auditing is T-SQL.** `CREATE SERVER AUDIT ... TO EXTERNAL_MONITOR` plus a server audit
specification, and the diagnostic category `SQLSecurityAuditEvents` on the instance. Either alone
records nothing. Neither module renders the audit.

**Redirect needs ports.** `connection_type: Redirect` has clients talk to the node on TCP
11000-11999 after the first hop; the platform's NSG rules allow it inside the network, a client
firewall that passes 1433 only does not. The public endpoint is proxied on 3342 regardless.

**The public endpoint has no firewall of its own.** `enabled_with_firewall` is a rule on the
subnet's NSG for 3342; with a platform-owned subnet it is an open entry for the platform team.

**Defender for SQL is a subscription plan.** The instance-level threat-protection setting binds the
instance to it; the plan itself is the platform's, and an alert needs both.

**The modules disagree on defaults.** Zone redundancy (`true` in Terraform, `false` in Bicep), the
connection policy (`Default` against `Proxy`), backup storage (`GRS` / `Geo` in both, against the
guardrail's `Zone`); every decision is written on the call.

**Vulnerability assessment is the classic form.** A storage account reachable from the instance,
with the identity's role on it; the express configuration without storage exists for a logical
server only. Off until a storage account is named.

**Bicep has no private endpoint and no metrics in the module.** A private endpoint for a caller in
an unpeered network is an authored `Microsoft.Network/privateEndpoints` (`managedInstance`), and
the module's diagnostic setting carries logs only, so metrics are a second authored setting.

**GeoZone is not a Terraform value.** The module (and the provider) spell backup storage `LRS`,
`ZRS`, `GRS`; a `GeoZone` answer is recorded as forced to `GRS` with the module as forced_by, or
the instance is rendered authored.

## Not covered here, and why

Azure SQL Database (the sql-database set), SQL Server on a VM, instance pools, the free offer,
the next-generation General Purpose variant, failover groups and secondaries (the second region
is recorded as an open entry), Windows authentication for Entra principals, the link feature to
SQL Server, restore and point-in-time create modes, and long-term-retention immutability each
carry decisions of their own and have no question set; a request for one is said out loud, not
improvised.
