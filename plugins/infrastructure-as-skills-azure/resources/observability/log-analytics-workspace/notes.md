# Log Analytics workspace — what the question set cannot express

## Fixed at creation

- **The region.** Logs live where the workspace lives; moving means a new workspace and a
  gap in the data.
- **The name, for 14 days after a delete.** Soft delete reserves it, so a recreate inside
  the window is not a clean start.
- **A capacity reservation's commitment period**, once entered.

## Ordering

The workspace exists before anything that routes to it. That is obvious and still the
common failure, because a diagnostic setting with a dangling workspace id fails at apply
with a message about the *setting* rather than the missing target. In a spec with
`composition`, the module holding the workspace is a `needs` of every module that
diagnoses into it.

## Pitfalls

**Ingestion and query are separate switches.** `internet_ingestion_access_type` and
`internet_query_access_type` (azurerm 5.x; the AVM module still takes the 4.x bools) are independent, and a workspace with ingestion open and query
closed accepts everything and shows nothing to anyone outside the network — which reads
like a broken agent rather than a configuration choice.

**Private access needs an AMPLS, not a private endpoint.** The Azure Monitor Private Link
Scope is a separate resource with tenant-wide effects: linking a network to it changes
resolution for every agent in that network, including ones reporting to other workspaces.
This is platform infrastructure, and a workload deployment should reference one rather
than create it.

**A daily cap drops data, it does not slow it.** Once the quota is hit, ingestion stops
until the reset — which is the moment an incident is loudest. The cap resets at a time
that depends on the workspace's creation, not at local midnight.

**Retention has two layers.** Interactive retention is what KQL queries reach;
long-term retention beyond it is cheaper and is not queryable without a restore. A
"retained for two years" answer usually means the second, and a dashboard built against
the first will be empty.

**Default table retention versus per-table retention.** The workspace-level answer is a
default; individual tables can override it, and a table set longer than the workspace
keeps billing after someone has lowered the workspace value to save money.

**Diagnostic settings are not owned by this resource.** They live on the emitting
resource, so removing a workspace leaves settings pointing at nothing — and the resource
keeps reporting the setting as present.
