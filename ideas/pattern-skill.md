# Pattern skill

**Status:** sketch - the largest open piece of the plugin

## Idea

A pattern composes resources into a whole system and owns what no single question set can:
the wiring. `private-webapp` would be the first - App Service, storage, Key Vault, a
database, private, managed identity throughout. It pre-answers the resource questions the
pattern implies, asks only what remains, and holds the identity graph (who -> what -> which
role), the secret flow (app setting -> Key Vault reference), the private endpoints with
their DNS and the diagnostics.

Requirements choose the pattern: "a web application with a database, internal" selects
`private-webapp`, and the customer confirms the picture, not the resource list.

## What exists already

- The composition contract is specified: `spec.md` has `wiring:`, `patterns/` is named in
  `README.md` and the plugin manifest knows the convention (`./patterns/` enters
  `plugin.json` in the same commit as its first skill).
- The wiring of `examples/chatbot` and `examples/chatbot-rag` - roles between resources,
  the shared private link, the order identity -> vault -> consumer - is what a pattern
  would own. Both were written by hand.
- AVM pattern modules (`private-link-private-dns-zones`, `hub-networking`) are candidates
  for what a pattern wraps rather than re-implements.

## Open questions

- `wiring:` as a schema rather than an example: every edge validated against `resources:`,
  every role against the Azure built-in roles, no module reaching into another.
- The diagram at pattern scale: grouped by tier and subnet, identity edges on their own
  track, a decisions panel per tier rather than per resource.
- A pattern description costs listing budget; one skill per pattern will not scale either.
  Whether patterns route like families (one trigger, a routing table) is to be decided
  with the second pattern, not the first.
