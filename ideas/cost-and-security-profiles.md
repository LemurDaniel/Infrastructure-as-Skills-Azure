# Cost estimate and optimisation profiles

**Status:** sketch (the profiles exist since `priority`; the estimate is the open part, 2026-10-26)

## Idea

Every spec gets a rough monthly cost estimate, per stage, shown to the customer in Phase 4
beside the design list: what the system costs to run, which parts cost the most, and what an
answer they gave cost them. The customer answers `priority` (cost, balanced, protection) and
`expected_load` without knowing what they buy; the estimate is where they see it.

The profiles are already a deployment question (`priority`): `cost` keeps the non-production
stages cheaper, `protection` builds every stage like production and switches on the records an
investigation needs. What is missing is the number next to the answer.

## Sketch

- **Input:** the spec's resources with their SKU, size, replication, retention and instance
  count - the decisions the question sets already record - per stage, so the savings of
  `non_production_savings` show up as a second column, not a footnote.
- **Prices:** the Azure Retail Prices API (public, no auth), looked up live at estimate time
  and never remembered, like AVM versions; the region is the stage's `location` parameter.
- **Mapping:** each resource question set declares which of its decisions are billing meters
  (`sku`, `vcores`, `instance_count`, `replication`, `retention_days`, a per-GB ingestion). A
  small `cost:` block per set, not a table in the skill, so a new resource brings its own.
- **Usage-based meters** (ingestion, requests, egress, messages) need an assumption. The
  estimate takes it from `expected_load` and says so; it never invents a volume the customer
  did not give.
- **Output:** one table in Phase 4, per stage and in total, the three or four biggest lines
  named in the customer's words ("der Datenbank-Server", "die Schutzschicht vor der
  Webseite"), and the cost of each decision that moves it - protection copy, zone redundancy,
  a Front Door in front of a public part.
- **A profile only moves decisions that are not security-shaped,** in the cost direction
  (same rule as `non_production_default`); the estimate shows what a switch costs or saves
  and never offers to buy the security floor off.

## Open questions

- The estimate is an order of magnitude, not a quote; it says so, with a range rather than a
  single number.
- Where the per-resource `cost:` block lives: in `questions.yaml` beside `renders`, or in a
  file of its own so the check script can require it for every set.
- Reserved instances, savings plans and enterprise discounts are the customer's, not the
  plugin's: the estimate is list price and says so.
- Whether the estimate is a render output (a file beside `infra-decisions.md`) or only a
  Phase 4 table.
