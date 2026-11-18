# AI Search - what the question set cannot express

## Fixed at creation

- **The tier.** A service does not move between tiers; it is rebuilt and every index
  reloaded. Basic to standard is a migration.
- **The name.** Global, lowercase, 2-60 characters, part of the endpoint
  `<name>.search.windows.net`.
- **The hosting mode** (`highDensity`, standard3 only).
- **The region.**

## Ordering

The identity and its roles on the data sources (storage, Cosmos DB), then the service, then its
private endpoint and the shared private links to the data sources, then the role assignments on
the service, then the consumers. The workspace before the diagnostic setting. Indexes,
indexers and skillsets are created by the application afterwards, with a data-plane call.

## Roles

A role on the service is a `wiring.role_assignments` entry with it as `to`. With keys off,
nothing reads or writes an index until one exists, so a service without a role for its
caller works and is of no use to anyone. A consumer nobody has named is an `open:` entry
(key `wiring.role_assignments`) owned by the workload owner, blocking apply.

The roles are the narrow ones - `Search Index Data Reader` for a query client, `Search Index
Data Contributor` for whatever loads documents, `Search Service Contributor` for whatever
manages indexes and indexers. The roles the service's own identity needs on what an indexer
reads (a storage account, a model) are entries with the service as `from`.

## Pitfalls

**Replicas are availability, partitions are capacity.** Adding partitions does not make queries
survive an outage; replicas do. Two for query availability, three for indexing as well.

**Capacity changes are slow and tier-bound.** Search units (partitions times replicas) are the
bill; scaling is in place but takes minutes, and a tier cap (basic: 3 units) is not a setting.

**A closed service needs shared private links for its indexers.** With
`public_network_access: disabled` an indexer cannot reach a data source over the public
endpoint. It needs a *shared private link resource* to the source, approved on the source's
side - wiring, owned by a pattern, and a step that stays "Pending" until approved.

**Keys off means roles on, in both directions.** The clients need `Search Index Data
Reader` or `Contributor`; the service's identity needs the reader role on every data source it
indexes and, for a skillset calling a model, `Cognitive Services OpenAI User` on that account.
The admin key is gone, so a deployment script that created an index with it breaks.

**The modules disagree on defaults.** Replica count (Terraform 1, Bicep 3) and local
authentication (Terraform on, Bicep off) differ, and both leave public access on; every
decision is written on the call.

**The query log carries query text.** It can hold personal data typed by a user.

**Log category names are the platform's.** `OperationLogs` is checked against `az monitor
diagnostic-settings categories list --resource <service id>` before a render.

## Not covered here, and why

Indexes, indexers, data sources and skillsets (data plane), shared private link resources,
semantic configuration, the knowledge store and an integrated vectorizer carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
