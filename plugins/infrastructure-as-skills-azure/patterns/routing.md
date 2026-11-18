# Patterns

Whole systems, reached from [iac-authoring](../core/iac-authoring/SKILL.md) in Phase 0. A
pattern names the parts of a system, asks the few questions only it can ask, answers what
the system implies in the parts' question sets, and owns the wiring between them. The
request picks the pattern, and the customer confirms the design, never a resource list.

Routing table - what the request describes picks the pattern:

| The request describes | Pattern | Parts |
|---|---|---|
| A chat app or assistant that answers from the customer's own documents: "chat app with RAG", "Chatapp mit RAG", a chatbot over internal knowledge, question answering over files | `ai-chat-rag/pattern.yaml` | One application, language and embedding model, search index, document storage; chat histories and a company sign-in on request |
| A web application with a database behind it: "web app with a database", "Webanwendung mit Datenbank", an internal business application, a portal with its data | `private-webapp/pattern.yaml` | One application, a relational database, file storage on request |
| An API whose requests are processed asynchronously: "API with a queue", "Bestellungen entgegennehmen und verarbeiten", event-driven integration between systems, an API in front of functions | `event-integration/pattern.yaml` | API gateway, functions, a queue and/or events between them |
| Two or more services as containers, whether they call each other or not: "microservices", "mehrere Container", an API with a background worker nobody calls, services on Container Apps | `container-microservices/pattern.yaml` | Two container apps in one environment, image registry, an identity each |
| A single resource or a list of resources ("a storage account", "a Key Vault and a VNet"), or a system none of the rows describes | *no pattern* | The interview runs on the resources alone, as without this table |

Two rows fit, or none clearly does: ask once which system it is, with the candidates'
`summary` as the options and "none of these" as the last one. Never bend a request into a
pattern - a system that only resembles one loses more to wrong pre-answers than it gains.

## Then

1. Read the pattern through the digest, never the file:
   `python3 <plugin>/core/iac-authoring/scripts/interview_digest.py --pattern <id> <sets...>` -
   its asks join the interview's batch under their topics, its boundaries are said out loud.
2. Once its asks are answered, `apply_pattern.py` writes the pattern's share of the spec -
   the parts with their purposes, the pre-answers and the wiring, every value
   `source: pattern`. The rules are in
   [pattern-format.md](../core/iac-authoring/references/pattern-format.md#in-the-interview).

## True for every pattern

**A pattern answers, the customer decides.** What the customer says wins over a pre-answer,
and the departure is recorded `overridden` with what it changes in the wiring. A pattern
never answers a question the customer is asked, one a requirement derives, or one the
deployment decides once for every resource - its pre-answers are defaults and references
between its own parts.

**The network is not a part.** The virtual network, its security groups, private endpoints,
DNS zones, the workspace and Application Insights follow from the deployment decisions for
any system; a pattern adds none of them and its wiring names none.

**More than the pattern is the interview's.** A resource the request names beyond the parts
("...plus an Event Hub") is interviewed through its question set as always; its connections
to the parts are added to `wiring` by the run and recorded `stated`, and from then on the
wiring is no longer `source: pattern`.

**A pattern is data, not a skill.** A directory here holds a `pattern.yaml` and never a
`SKILL.md`: a skill per pattern would spend the listing budget the entry skill needs.
