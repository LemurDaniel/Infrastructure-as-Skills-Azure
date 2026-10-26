# Azure data resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| Cosmos DB, Cosmos, NoSQL, document database, conversation history store | `cosmos-db/questions.yaml` | [notes](cosmos-db/notes.md) - API for NoSQL only |
| Azure SQL, SQL database, SQL Server, Azure SQL Database, elastic pool, serverless SQL, TDE | `sql-database/questions.yaml` | [notes](sql-database/notes.md) - Azure SQL Database (logical server and databases); not Managed Instance (own set below) |
| PostgreSQL, Postgres, flexible server (Postgres) | `postgresql-flexible-server/questions.yaml` | [notes](postgresql-flexible-server/notes.md) |
| MySQL, flexible server (MySQL) | `mysql-flexible-server/questions.yaml` | [notes](mysql-flexible-server/notes.md) |
| Redis, cache, Managed Redis, session store | `redis-cache/questions.yaml` | [notes](redis-cache/notes.md) - Azure Managed Redis only; the older Azure Cache for Redis has no question set |
| SQL Managed Instance, Managed Instance, SQL MI, managed SQL Server, SQL Agent, cross-database queries, lift-and-shift SQL Server, Instanz | `sql-managed-instance/questions.yaml` | [notes](sql-managed-instance/notes.md) - the instance in its delegated subnet; 4-6 h deployment; not Azure SQL Database |
| Data Factory, ADF, data pipelines, ETL, ELT, copy activity, data flows, integration runtime, Datenintegration | `data-factory/questions.yaml` | [notes](data-factory/notes.md) - the factory and its runtimes; pipelines are content |
| Purview, Microsoft Purview, data catalog, data governance, data map, lineage, Datenkatalog | `purview-account/questions.yaml` | [notes](purview-account/notes.md) - one account per tenant; default is to reference the platform's |
| MongoDB, Cassandra, Gremlin, Table API | *not yet written* | Other Cosmos DB APIs decide differently; not covered by the NoSQL set |
| Storage account, blob, data lake | see the [storage](../storage/routing.md) family | Not here |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, `local_auth` and `key_management` before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**Data is where the customer's requirements land.** `outage_impact` decides zone
redundancy and a second region, `data_loss_tolerance` decides how far back a restore reaches,
`data_access_pattern` decides tiering where a resource has it, `data_residency` decides
which regions a replica or a geo copy may land in, and `backup_isolation` whether a
separate backup store is wanted - which Cosmos DB meets by itself. The customer is asked nothing
new; the engineer's own questions are the data model's.

**What cannot be changed after creation is the decision to take slowly.** A partition key,
the capacity mode, the free-tier flag, zone redundancy of an existing region, a
customer-managed key: each is fixed or one-way, and each question set says which in its
`why`.

**A data store has two permission systems when it is a service with its own data roles.**
Azure RBAC governs the account; the service's own roles govern the data. A deployment that
grants only the first has a working account nobody can read.
