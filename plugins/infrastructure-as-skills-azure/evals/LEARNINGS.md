# Eval learnings

One entry per failure that was found and fixed, newest first. `baseline.json` holds the
numbers; this file holds why a case failed and what changed. Write the entry before the
fix is committed, and put the commit hash in once it exists.

| Field | Content |
|---|---|
| Case, date | `<case>`, `YYYY-MM-DD` |
| Symptom | Which grader failed, in how many runs (e.g. 1/3) |
| Cause | Skill, reference, grader or case prompt. Say if the grader was too strict or flaky rather than the output wrong |
| Fix | What changed, with the commit |
| After | Rate after the fix (e.g. 3/3) |

## Entries

### `trigger-workload-request` and three more, on Haiku, 2026-10-27

- **Symptom:** `skill-fired` failed on Haiku in four cases: `trigger-workload-request` 2/4,
  `language-en-first-question` 2/4, `requirements-stated` 3/4, `claude-md-section-replaced`
  3/4. Sonnet fired 4/4 everywhere. A run that never loads the skill writes no spec, so the
  spec graders fail behind it.
- **Cause:** The `iac-authoring` description. It said what the skill is for ("the entry
  point ... Use whenever ...") but not when to load it, and Haiku answered the request
  directly - a prompt saying "your first message is graded" pushes that way.
- **Fix:** The description now opens with "Load this FIRST, before your first reply", quotes
  the request that once failed ("eine Chatapp in Azure mit RAG") and ends "never answer such
  a request from memory". 479 characters, listing at 88% of its budget.
- **After:** on Haiku the skill fired 14/14 in those four cases; `trigger-workload-request`
  and `language-en-first-question` 100%. `requirements-stated` (0/2) and
  `claude-md-section-replaced` (2/4) still fail inside the skill - the `requirements` group
  and the CLAUDE.md sync are dropped - which is the size of `iac-authoring`, not its trigger.

### `diagram-before-code-after-change`, 2026-10-25

- **Symptom:** The case never ran (invalid `case.yaml`: the `llm` grader used `target` and
  `prompt` instead of `focus` and `criteria`). Once loadable it failed 0/3 on
  `no-code-before-signoff`, `asks-for-signoff` and `diagram-skill-fired`: the plugin wrote the
  whole IaC, tests included, without drawing or asking.
- **Cause:** The plugin. The sign-off rule existed, but the request said "dann schreibe den
  Terraform-Code" and nobody could answer, and the run took the order over the rule.
- **Fix:** A paragraph in Phase 5 of `iac-authoring`: a request for code is not the sign-off,
  and a run nobody can answer ends after the diagram with the question and no code. Grader
  keys corrected.
- **After:** 3/3 on `no-code-before-signoff` and `asks-for-signoff`. `diagram-skill-fired`
  stays 0/3: it is an indicator, and the run names the diagram without calling the skill.

### `diagram-no-invented-lines`, 2026-10-25

- **Symptom:** `no-invented-purposes` 0/3, `has-sql` 1/3.
- **Cause:** Both graders. The request calls the app "Bestell-App", so a purpose for the app
  service is a fair reading; only a purpose for storage or SQL is invented. Azure SQL has no
  question set, so it is a module entry and an open item, not a `resources:` key.
- **Fix:** `no-invented-purposes` forbids a purpose for storage-account and sql-*; `has-sql`
  accepts any mention of `sql-database` or `sql-server`. A rewrite first turned `` into a
  backspace (0/3 again): test a pattern from the file on disk, not from the edit.
- **After:** 3/3 on both.

### `diagram-external-and-optional`, 2026-10-18

- **Symptom:** `no-invented-cache-call` failed, 1 of 1 runs. The spec carried
  `{ from: app-service, to: redis-cache }`.
- **Cause:** Two, and only one was the output. The **grader was too strict**: the request says
  "ein Redis Cache für die Sitzungen" and the cache is for the API's sessions, so a call from
  the app is a fair reading; the prompt does not settle it either way. The other was a real
  **script bug** the run exposed: `new_diagram.py` treated every access endpoint that is not a
  resource key as an actor, so `redis-cache` (named in `access`, absent from `resources:`) was
  drawn in the external zone as if the customer's deployment did not build it.
- **Fix:** Grader removed with the reason in the case; the script now accepts only `internet`,
  `users` and `external:<name>` as actors and warns and drops any other unknown endpoint;
  `run_diagram_tests.py` asserts it (the `public-webshop` fixture names `redis-cache`). Same
  run: a subnet written as `virtual-network.<name>` is drawn as `<name>`. Commit: `a0d1439`.
- **After:** The remaining 8 graders of the case 8 of 8 (1 run). The other two diagram cases
  have not been run yet - the first run cost $1.60 for one case, so a `runs: 3` measurement of
  all three is about $15 and was not started.

## language-en-first-question (and the `language/` group)

- **Symptom:** An English request ("I need a chat app with an MCP server ...") got the target,
  module and naming questions in German: the skill carries those blocks as German wording and
  the model copied them.
- **Cause:** The skill never said that the blocks are templates for `context.language`, and the
  language was set after the first question.
- **Fix:** Phase 0 of `iac-authoring` now takes the language from the request before anything is
  asked and says the German blocks are the German wording of a question. Cases:
  `language-en-request`, `language-de-request`, `language-en-first-question`.
- **Grader notes:** The first version of `language-en-first-question` judged "everything the
  message asks" and failed an all-English message that asked nothing (headless runs write the
  spec at once when `AskUserQuestion` is not granted); the criterion is now "nothing is German".
  Headless, the first message is prose, not an `AskUserQuestion` call, so the case grades the
  final message.
- **After:** `language-en-request` and `language-de-request` all graders (1 run each);
  `language-en-first-question` 3 of 3 runs, all graders. The cases were not run against the
  skill from before the fix, so they are not yet shown to fail without it.
