# Evals

End-to-end cases for `claude plugin eval`: a request goes in, the plugin interviews,
writes `infra/infra-spec.yaml` — and the graders check the spec.

```powershell
claude plugin eval plugins/infrastructure-as-skills-azure --allow-tools Write Edit
```

`Write` and `Edit` are needed because the run writes the spec. No shell: on Windows the
eval sandbox has no backend and refuses any case that grants one, so `check_spec.py` and the
diagram run outside the suite. How to run, check and read the suite is in the repo's
`plugin-evals` skill (`.claude/skills/plugin-evals/`). Results land in `evals/results/`,
which is ignored.

## Layout

One directory per group, one per case below it. The runner finds `**/case.yaml`, so the
grouping costs nothing; a case's `prompt.md` reaches the plugin with `plugins: ["../../.."]`.

| Group | Grades | Cases |
|---|---|---|
| `spec/` | The interview's output, `infra/infra-spec.yaml` | `vague-public-dev`, `module-source-authored`, `requirements-stated` |
| `diagram/` | What the spec carries for the picture | `diagram-*` |
| `trigger/` | That a request triggers the plugin at all | `trigger-workload-request` |
| `language/` | The language of the person is the language of everything said to them | `language-en-request`, `language-de-request`, `language-en-first-question` |
| `process/` | The order of the run: after a change of the spec, diagram and sign-off come before any code | `diagram-before-code-after-change` |
| `sync/` | The version gate and the CLAUDE.md section in a repository that already holds a spec (scaffolded) | `plugin-newer-halts`, `claude-md-section-replaced` |
| `render/` | The code the render writes, for the few rules a spec cannot show | `bicep-secret-placeholder-once` |

## The cases

Chosen along the dimensions where this plugin can go wrong, so three cases cover the
most different situations rather than three variations of one:

| Case | Target | Env | Exposure | Network | Workspace | Scenario |
|---|---|---|---|---|---|---|
| `vague-public-dev` | Terraform | development | public | none | reference | **Missing information** |
| `module-source-authored` | Terraform | development | private | none | - | A stated departure from the AVM default: `module_source: authored`, no `implementation: avm` |
| `requirements-stated` | Terraform | production | - | - | - | All five customer requirements in plain words, none at its default; the access tier derives |
| `diagram-no-invented-lines` | Bicep | staging | - | - | - | Three resources, **no call named**: no line may be invented |
| `bicep-secret-placeholder-once` | Bicep | development | public | none | - | Spec and diagram already signed off, Bicep asked: each secret placeholder carries `@onlyIfNotExists()`, no lookup of existing secrets, no secret value as a parameter |
| `plugin-newer-halts` | Terraform | development | public | none | - | The spec carries `plugin_version: 99.0.0`: the run halts, changes and writes nothing, and says to update the plugin |
| `claude-md-section-replaced` | Terraform | development | public | none | - | A CLAUDE.md with an older plugin section (no rev) between the team's own text: replaced, once, team text intact, the spec stamped |

The two `sync/` cases start from a scaffold (`scaffold.sh` in the case directory, run with
`--scaffold`): the eval sandbox has no shell, so the agent compares versions and edits the
section by hand with Read and Edit, which is also the path on a machine without Python. The
scripts are tested by `run_plugin_version_tests.py` and `run_claude_md_tests.py`; the rule that a section with a
higher rev is left alone is only there, since an eval run for it costs real money and the script test is free.

The `diagram-no-invented-lines` case tests the half of the diagram a run can reach: the spec. The
picture is drawn from `wiring.access`, `wiring.purposes` and `wiring.optional` and from
nothing else, so the cases grade that the spec carries what the request said and nothing
it did not - an invented line in a picture the customer signs off on is a decision nobody
made. The drawing itself cannot run in a case (no shell in the eval sandbox on Windows) and
is tested separately, deterministically and for free:

```powershell
python3 plugins/infrastructure-as-skills-azure/core/iac-diagram/tests/run_diagram_tests.py
```

Fixture specs go in, assertions on the `.drawio` come out: zones, one bundled endpoint icon,
line count and colour, no Python syntax in a label, solid rounded containers, the fallback box
for a type without an icon. Run it after any change to `new_diagram.py`.

The three `language/` cases test that `context.language` follows the request: the spec's
customer-facing text, the final message and, in `language-en-first-question`, the very first
interview question (the skill carries it as German wording). The English cases close with the
English translation of the usual paragraph - a German paragraph would itself signal German -
and `language-en-first-question` has only a one-line note, because its final message *is* the
question that is graded.

Every case ends the same way, so every case can be graded the same way: no one answers
follow-up questions (a headless run cannot), and neither a diagram nor code is wanted —
only the spec.

## What the graders check

Mostly `regex` over `infra/infra-spec.yaml`. A regex reads the whole file identically every
run, costs nothing, and its failure says exactly which decision went wrong. Each case has:

- **The decisions the prompt settled** — exposure, ownership, ranges, retention.
- **What must not appear** — a created vnet that was only referenced, an invented address
  range, subscription id or resource group. These are the failures that look plausible and
  surface at apply time, which is why they are weighted up.
- **The process** — a plugin `Skill` fired, `azure-resources` or `iac-authoring` (an indicator, not scored against the no-plugin arm),
  `naming.yaml` written for a Terraform target and not for a Bicep one, no `.tf`/`.bicep`
  written before confirmation.

`check_spec.py` — the contract check covering sources, enums, backend attribute spellings
and composition — runs on the produced specs after the suite, not inside it.

`llm` graders only where a regex cannot see it - the language of the final message, the
order of a run, a halt that is said rather than written - each on the short final message
only, with concrete PASS and FAIL conditions. The judge is Haiku (`--judge-model`) and costs
a fraction of a cent per verdict; the agent runs are what a suite costs.

## In CI

`.github/workflows/plugin-evals.yml` runs the suite on every pull request that changes the
plugin: on Haiku (`--model haiku`, about a fortieth of the Opus price per token), three runs
per case in parallel so that an unstable decision shows, no baseline arm, an $8 ceiling. It
runs one case per call, so the log says which case it is on and how long the rest will take,
and merges the results (`merge_eval_results.py`). It reports and does not gate: Haiku scores
lower than the model `baseline.json` was taken on, so its rates are compared with Haiku's
own. The pull request gets one comment, updated on every push: pass rate per case, unstable
cases, the change against the previous version on the same model, a link to the run in the
dashboard. A release measurement is started by hand (`workflow_dispatch`) with the model it
needs.

Every run is recorded on the `eval-history` branch by `record_eval_history.py` (repo skill
`plugin-evals`): `index.json` with one summary per run - plugin version, model, trigger,
pass rate per case - and the full result beside it. The eval dashboard
(`eval-agent/dashboard`) reads it and compares a run only with an older plugin version on
the same model.

## Keeping outputs good on the same scenarios

`runs: 3` per case is the consistency measurement: a grader that passes in two of three
runs is a decision the plugin does not pin down. Read those first — they are where a
question set lacks a default, a rule in `iac-authoring` is ambiguous, or the
description-to-spec mapping in Phase 0 guesses.

The method follows Hamel Husain's
[*Creating a LLM-as-a-Judge That Drives Business Results*](https://hamel.dev/blog/posts/llm-judge/):

1. **One expert decides what good is** — the repository owner, not a generic metric.
2. **Binary pass/fail with a written critique**, never a 1–5 score. A critique detailed
   enough for a new colleague becomes the next grader or the next guardrail.
3. **Read the traces.** After a run, open the report and read the failed runs' specs before
   touching a grader. Group failures by cause and fix the most frequent first — usually in
   the plugin, not in the eval.
4. **Code checks before judges.** Anything expressible as a regex over the spec is one.
   Add an `llm` grader only for what a regex cannot see, and only after checking its
   verdicts against your own on a handful of runs — agreement on both passes and fails,
   not overall agreement.
5. **Every fixed failure becomes a case.** A bug found in a real run (like the
   `name / resource-group` label overflow) gets a case or a grader, so it stays fixed.

Re-run the suite after any change to a question set, the guardrails or `iac-authoring`,
and after a model update — and compare against `baseline.json`, the committed pass rates
of the last accepted run. `show_eval_result.py` does the comparison and flags a grader
whose rate dropped as REGRESS; `--update-baseline` writes the new snapshot once the run is
read and accepted. Results stay ignored; the baseline is the one thing a run leaves
behind in git.

## Adding a case

Pick a combination the table does not have yet — a pattern skill once `patterns/` exists,
an extension run (a scaffolded repo that already holds a spec), a `custom` naming
convention, a user who contradicts themselves. Write the prompt as a real user would,
then one grader per decision the prompt settles and one per value it must not invent.
