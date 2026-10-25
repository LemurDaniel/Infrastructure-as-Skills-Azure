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
