# Patterns

**Status:** planned - branch `pattern-skills`, release 0.7.0

## Idea

A pattern composes resources into a whole system and owns what no single question set can:
the wiring. It pre-answers the resource questions the system implies, asks only what remains,
and holds the identity graph (who -> what -> which role), the secret flow (app setting -> Key
Vault reference), the private endpoints with their DNS and the diagnostics.

Requirements choose the pattern: "eine Chatapp mit RAG" selects `ai-chat-rag`, and the
customer confirms the picture, not the resource list.

## Decisions (2026-10-29, owner's call)

- **Patterns are data, not skills.** `patterns/<name>/pattern.yaml` beside a
  `patterns/routing.md`, reached the way `resources/<family>/` is: `iac-authoring` reads the
  routing table in Phase 0, no `SKILL.md`, no entry in `plugin.json`. The listing budget is at
  88% (1,768 of 2,000); a skill per pattern overflows at the second, one routing skill costs
  ~200 characters for a trigger `iac-authoring` already has ("Chatapp mit RAG", "web app",
  "API"). This reverses the plan in `README.md` and `CLAUDE.md` that `./patterns/` enters
  `plugin.json` with its first skill - both are corrected on the branch.
- **Four patterns on one branch**, so the format is proven on four shapes before it freezes
  for 1.0, not fitted to the first:

| Pattern | Parts | Wiring it owns | Drawn from |
|---|---|---|---|
| `ai-chat-rag` | App (App Service or Container App), Foundry, AI Search, Storage, Key Vault, Cosmos DB for history (optional), Application Insights | app -> Foundry / Search / Storage / Cosmos roles, Search -> Storage (indexer) and -> Foundry (embeddings), secret flow, endpoints | `chat-sandbox`, `chatbot-multi-rg`, the trigger eval |
| `private-webapp` | App Service, database (Azure SQL or PostgreSQL), Storage, Key Vault, Application Insights | app -> database (Entra auth), -> Storage, -> Key Vault references, VNet integration, endpoints | `ideas/` (no example) |
| `event-integration` | Front door or gateway (optional), API Management, Function App, Service Bus and/or Event Grid, Storage, Key Vault | gateway -> APIM -> function (chain), function -> bus send/receive roles, Event Grid delivery to the function, secret flow | `orders-integration` |
| `container-microservices` | Container Apps environment, several container apps, Container Registry, Key Vault, user-assigned identities, Application Insights | app -> app calls inside the environment, AcrPull per app, identity per app, ingress internal/external per app | none yet |

## The format (`pattern.yaml`)

```yaml
schema_version: 1
id: ai-chat-rag
title: { en: ..., de: ... }
selects_when: [...]          # request signals, for routing.md and the Phase 0 proposal
parts:                       # resource keys (instances with __), each required or optional
  app-service__web: { required: true }
  cosmos-db: { optional: history_store }   # an `asks` question decides it
asks:                        # pattern-level interview questions, same fields as a question set
  - id: history_store
    ...
pre_answers:                 # resource -> question id -> value, each with a why
  storage-account:
    shared_access_key_enabled: { value: false, why: ... }
wiring:
  access: [{ from, to, label }]
  role_assignments: [{ principal, scope, role }]   # built-in role names only
  secrets: [{ app, setting, vault, secret }]
composition: { granularity, modules }               # optional, as in iac-authoring
```

The spec records `deployment.pattern` (the id) and `source: pattern` on every pre-answered
value; precedence stays as `iac-authoring` has it (stated > carried > platform > pattern >
default). The user overrides a pre-answer and is told what the departure implies.

## Plan

1. **Format and checker.** `core/iac-authoring/references/pattern-format.md`;
   `check_pattern.py`: parts exist as question sets, every pre-answer names a question of its
   set and a value its `accepts` allows, `asks` follow the question-set format, every wiring
   endpoint is a part or an actor, every role a built-in role (a checked-in list); a test
   runner that breaks one rule per mutation.
2. **`wiring` as a schema in `check_spec.py`**: edges against `resources:`, roles against the
   same list, secrets against a vault in the spec. Today `wiring` is only example-shaped.
3. **Routing and Phase 0.** `patterns/routing.md` (request -> pattern, and "no pattern" as an
   answer); `iac-authoring` proposes a pattern before the batch, applies its pre-answers and
   asks its `asks` in the right topics; `interview_digest.py` reads a pattern beside the sets.
   `check_repo_consistency.py`: no `SKILL.md` under `patterns/`, every pattern routed.
4. **The four patterns**, in the order of the table, each with a fixture spec that passes
   `check_spec.py` and draws through `new_diagram.py` (diagram test per pattern).
5. **Evals**: one case per pattern (`patterns/` group): the pattern is chosen, its
   pre-answers land with `source: pattern`, its wiring is complete, nothing outside it is
   invented, a stated departure wins. Four new cases, `runs: 4` until measured.
6. **Docs**: `README.md` (layout, status, the reversal), `CLAUDE.md` (the structural
   constraint: `patterns/` is not declared), `spec.md` (`deployment.pattern`),
   `PROGRESS.md`.

## Open, decided on the way

- Whether a pattern can be combined with resources outside it ("Chatapp mit RAG plus eine
  Event-Hub-Anbindung") - probably yes, the extra resource is interviewed as today.
- AVM pattern modules (`private-link-private-dns-zones`) wrapped by a pattern or not.
- The diagram at pattern scale: grouped by tier, identity edges on their own track.
- Whether `examples/chat-sandbox` is regenerated from `ai-chat-rag` on this branch or after.
