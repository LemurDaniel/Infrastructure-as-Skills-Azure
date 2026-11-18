# The pattern format

A pattern composes resources into a whole system. A question set knows one resource; what
no question set can own is what lies between two of them - which identity may do what on
which resource, which setting reads which secret, which part exists at all. A pattern
holds that: `patterns/<id>/pattern.yaml`, reached through
[`patterns/routing.md`](../../../patterns/routing.md).

| File | Where | Purpose |
|---|---|---|
| `pattern.yaml` | `patterns/<id>/` | The parts, the asks, the pre-answers and the wiring of one system. This file's subject |
| `routing.md` | `patterns/` | Routes a request to a pattern, or to none |

A pattern is data, never a skill: no `SKILL.md`, no entry in `plugin.json`.

## Shape

```yaml
schema_version: 1

id: ai-chat-rag                  # the directory's name
title:   { en: ..., de: ... }
summary: { en: ..., de: ... }    # one sentence: the proposal the customer hears
selects_when:                    # the request signals that choose it
  - "chat app with RAG / Chatapp mit RAG"
boundaries:                      # what the pattern does not own, said out loud
  - "The models are the customer's choice from the catalogue."

parts:                           # the resources of the system, by spec key
  app-service__chat:
    purpose: { en: "Chat application", de: "Chat-Anwendung" }
  key-vault:
    when: { ask: sign_in, equals: company_accounts }
    purpose: { en: "Secret of the company sign-in", de: "Geheimnis der Firmenanmeldung" }

asks:                            # what only the pattern can ask - question-set format
  - id: sign_in
    ask: { en: ..., de: ... }
    type: enum
    accepts: [application, company_accounts]
    default: application
    resolved_by: interview
    topic: security
    plain: { en: "Sign-in: {value}.", de: "Anmeldung: {value}." }
    why: >
      ...

pre_answers:                     # part -> question id -> the answer and its reason
  search-service:
    managed_identity:
      value: system_assigned
      why: >
        The indexer reads the documents with the service's own identity ...
  key-vault:
    secret_placeholders:
      value: [entra-client-secret]
      why: >
        ...

wiring:
  access:                        # who reaches what - the lines of the picture
    - from: users
      to: app-service__chat
      label: { en: "HTTPS 443", de: "HTTPS 443" }
  role_assignments:              # which identity holds which role on which part
    - { from: app-service__chat, to: search-service, role: Search Index Data Reader }
  secrets:                       # which app setting reads which secret
    - app: app-service__chat
      setting: MICROSOFT_PROVIDER_AUTHENTICATION_SECRET
      vault: key-vault
      secret_name: entra-client-secret
      when: { ask: sign_in, equals: company_accounts }
```

## Fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | The directory's name. The spec records it as `pattern.id`; renaming one orphans every spec that names it, so treat it as an interface. |
| `title`, `summary` | yes | The name and one sentence, `en` and `de`: what the customer is told is being built. |
| `selects_when` | yes | The phrases of a request that choose this pattern, both languages in one line. `routing.md` carries a row for the pattern; the check fails without one. |
| `boundaries` | no | What a reader would expect the pattern to own and it does not. Said out loud in Phase 4, never improvised. |
| `parts` | yes | The resources, keyed as in a spec: `<set>` or `<set>__<instance>`. Each carries a `purpose` (`en`, `de`) - the spec's `meta.purpose` - and, where it does not always exist, a `when`. |
| `asks` | no | Interview questions in the [question-set format](question-set-format.md): `resolved_by: interview`, a `topic`, no `renders`, and always a `default`, so the pattern gives a system before anyone answers. An id the deployment set uses is refused. |
| `pre_answers` | no | `<part>: { <question id>: { value, why } }`, the question being one of the part's set; `deployment:` for the deployment set. Several answers that differ by `when` are a list, the first that holds is taken. |
| `wiring.access` | no | `{ from, to, label }`: a part or an actor (`users`, `internet`, `external:<name>`) on each side. |
| `wiring.role_assignments` | no | `{ from, to, role }`: the identity, the part the role is on, a role of [built-in-roles.yaml](built-in-roles.yaml). |
| `wiring.secrets` | no | `{ app, setting, vault, secret_name }`: the application, the name of its setting, the key vault part, the secret's name. |
| `composition` | no | `granularity` and `modules`, as in [spec.md](spec.md#modularity), where the system fixes the module split. |
| `when` | no | On a part, a pre-answer or a wiring line: `{ ask: <id>, equals \| not_equals \| contains: <value> }`, or a list of them that must all hold. |

## What a pattern may answer

A pattern is applied without anyone being asked, so its reach is narrow on purpose.
`check_pattern.py` refuses a pre-answer for:

- **a question the customer is asked** (`resolved_by: interview`) - the models, the
  databases, the retention: the pattern never answers for them;
- **a question a requirement derives** (`answer: { question, map }`) - replication from the
  outage answer: the customer's answer decides it;
- **a question that inherits a deployment decision** (`answer: { deployment }`,
  `answer: { context }`) - exposure, local authentication, keys: one decision per system,
  made in the deployment set.

What is left is what a pattern knows better than a default: a `default` the wiring depends
on (an identity that must exist because a role is granted to it), a `required` value
nothing else can give (which storage account is the function app's host storage), and the
contents of a list the set says a pattern fills (`secret_placeholders`, `database_users`).
A value equal to the set's default is still worth writing where the wiring breaks without
it: `source: pattern` then says why it must not be changed lightly.

A reference between parts is `{ resource: <part> }`, as in a spec; a pattern knows no
resource outside itself.

## What the wiring must satisfy

The conditions make a pattern several systems at once, so the check resolves **every
variant** - each value of each enum or bool ask - and holds each to the same rules:

- An access line and a role assignment name only parts that exist in that variant.
- A role goes to **a part that has an identity of its own**: a `user-assigned-identity`
  part, or a part whose `managed_identity` (the pre-answer, else the set's default) is
  `system_assigned`. A part that acts with a user-assigned identity never holds the role
  itself - the identity does - and a part with `none` cannot hold one.
- A role is a name of `built-in-roles.yaml`; a data-plane role (Cosmos DB's) only on its own
  service.
- **A role is explained by an access line**: the part that acts with the identity reaches
  the part the role is on. A role without a connection is a right nobody asked for.
- A user-assigned identity is used: some part names it in `user_assigned_identity_ids`.
- A secret is one the vault's `secret_placeholders` pre-answer creates, and an identity of
  the application holds a secret-reading role on that vault.

## In the interview

1. **Choosing.** Phase 0 reads `patterns/routing.md` once the request or the description
   says what the system is. One row fits: the pattern is proposed in one sentence (its
   `summary`) with the design, never as a question of its own - Phase 4's tick list is where
   the customer confirms it. Two fit, or it is unclear: one `AskUserQuestion`, the
   candidates' summaries as options, "none of these" last. None fits: no pattern, and the
   interview runs on the resources alone.
2. **Reading.** `interview_digest.py --pattern <id>` prints the pattern and the sets of its
   parts. Its asks join the batch under their topics like any interview question.
3. **Applying.** With the asks answered, `apply_pattern.py <id> --answer <ask>=<value> ...
   --language <context.language> --environments <stages>` prints the pattern's share of the
   spec: `pattern:`, the parts under `resources:` with their purposes and pre-answers, and
   `wiring:`. The run puts it into the spec and resolves everything else as always - the
   customer's answers, the requirements, the deployment decisions, each set's defaults.
   Never work the conditions out by hand.
4. **Departing.** What the customer says wins. A pre-answer they contradict is recorded with
   their value and `source: { overridden: <reason> }`, and Phase 4 says what the pattern
   expected and what the departure changes (a part without its identity loses its roles).
   A part they do not want is left out with every wiring line that names it; a resource
   they add is interviewed through its set and wired by the run. A wiring list changed in
   either way is no longer `source: pattern` but `stated`.

## In the spec

```yaml
pattern:
  id:
    value: ai-chat-rag
    source: stated          # the request described it; asked when the person picked it
  answers:
    sign_in:
      value: company_accounts
      source: asked
```

Every value the pattern gave carries `source: pattern`. `check_spec.py` holds the spec to
it: a value recorded `source: pattern` is exactly what the pattern answers for the recorded
answers, so a value someone changed cannot keep the pattern's name.

## Validate

```powershell
python3 <plugin>/core/iac-authoring/scripts/check_pattern.py                  # every pattern
python3 <plugin>/core/iac-authoring/scripts/check_pattern.py ai-chat-rag      # one
python3 <plugin>/core/iac-authoring/tests/run_pattern_tests.py                # the rules, and every variant end to end
```

The test applies every variant of every pattern, runs `check_spec.py` on the result and
draws it: a pattern that passes gives a spec the plugin accepts and a picture with every
part and connection.

## Adding a pattern

1. A directory `patterns/<id>/` with a `pattern.yaml`; copy an existing one.
2. Name the parts first, then the wiring between them, then only the pre-answers the wiring
   needs. A pre-answer that merely restates a default the wiring does not depend on is
   noise in the spec.
3. Keep the asks few: each one doubles the variants a reviewer has to hold in mind. A
   question about one resource belongs in that resource's set.
4. Write the `boundaries` - above all what a reader would wrongly assume is included.
5. Add the row to `patterns/routing.md`, and run the two checks above.
