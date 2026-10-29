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
| `spec/` | The interview's output, `infra/infra-spec.yaml` | `vague-public-dev`, `requirements-stated` |
| `diagram/` | What the spec carries for the picture | `diagram-*` |
| `trigger/` | That a request triggers the plugin at all | `trigger-workload-request` |
| `language/` | The language of the person is the language of everything said to them | `language-en-request`, `language-en-first-question` |
| `sync/` | The version gate and the CLAUDE.md section in a repository that already holds a spec (scaffolded) | `plugin-newer-halts`, `claude-md-section-replaced` |
| `render/` | The code the render writes, for the few rules a spec cannot show | `bicep-secret-placeholder-once`, `app-code-untouched`, `bicep-rerender-keeps-names` |

## The cases

Chosen along the dimensions where this plugin can go wrong, so three cases cover the
most different situations rather than three variations of one:

| Case | Target | Env | Exposure | Network | Workspace | Scenario |
|---|---|---|---|---|---|---|
| `vague-public-dev` | Terraform | development | public | none | reference | **Missing information** |
| `requirements-stated` | Terraform | production | - | - | - | All five customer requirements in plain words, none at its default; the access tier derives |
| `diagram-no-invented-lines` | Bicep | staging | - | - | - | Three resources, **no call named**: no line may be invented |
| `bicep-secret-placeholder-once` | Bicep | development | public | none | - | Spec and diagram already signed off, Bicep asked: each secret placeholder carries `@onlyIfNotExists()`, no lookup of existing secrets, no secret value as a parameter |
| `app-code-untouched` | Bicep | development | public | none | - | Spec signed off, a .NET app beside it reads another key than the render outputs: no Write or Edit on `.cs`/`.csproj`, the mismatch named in the hand-over |
| `bicep-rerender-keeps-names` | Bicep | development | public | none | deployed root | A deployed root whose Key Vault name predates `<LOCATION>` in its pattern, re-rendered for an unrelated change: the name stays and `naming_convention` stays `default`; the `naming.yaml` pin is a script's, tested by `run_naming_tests.py` |
| `plugin-newer-halts` | Terraform | development | public | none | - | The spec carries `plugin_version: 99.0.0`: the run halts, changes and writes nothing, and says to update the plugin |
| `claude-md-section-replaced` | Terraform | development | public | none | - | A CLAUDE.md with an older plugin section (no rev) between the team's own text: replaced, once, team text intact, the spec stamped |

The two `sync/` cases start from a scaffold (`scaffold.sh` in the case directory, run with
`--scaffold`): the eval sandbox has no shell, so the agent compares versions and edits the
section by hand with Read and Edit, which is also the path on a machine without Python. The
scripts are tested by `run_plugin_version_tests.py` and `run_claude_md_tests.py`; the rule that a section with a
higher rev is left alone is only there, since an eval run for it costs real money and the script test is free.

The `diagram-no-invented-lines` case tests the half of the diagram a run can reach: the spec. The
picture is drawn from `wiring.access` and the resources' `meta.purpose` and from
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

The two `language/` cases test that `context.language` follows the request when it is not
the German the skill's own wording is written in: the spec's customer-facing text, the final
message and, in `language-en-first-question`, the very first interview question. The cases close with the
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
only, with concrete PASS and FAIL conditions. The judge is Sonnet (`--judge-model sonnet`; the CLI's default is Haiku, which failed fully English
messages as German) and costs about half a cent per verdict; the agent runs are what a suite costs.

## In CI

The suite is judged before a merge, on Sonnet at low effort (four runs per case, about
$15-25; repo skill `git-commit-conventions`, section 5). `.github/workflows/plugin-evals.yml`
runs the same on a Linux runner, by hand (`workflow_dispatch`): one case per call, so the log
says which case it is on and how long the rest will take, the results merged by
`merge_eval_results.py`, report only. There is no pull-request run. One was tried on Haiku:
it costs a twentieth per token, but scored 0% on every process, sync and render case and
was noisy on the spec cases - it measured the model, not the plugin.

Every run is recorded on the `eval-history` branch by `record_eval_history.py` (repo skill
`plugin-evals`): `index.json` with one summary per run - plugin version, model, trigger,
pass rate per case - and the full result beside it. The eval dashboard
(`eval-agent/dashboard`) reads it and compares a run only with an older plugin version on
the same model.

## Keeping outputs good on the same scenarios

`runs:` in each case's `prompt.md` is the consistency measurement, the same on every model:
4 per case, and 2 for the four cases that cost about $3 or more per suite on Sonnet
(`diagram-no-invented-lines`, `language-en-request`, `requirements-stated`,
`vague-public-dev`) - halved for cost, accepting that they can only read 0, 50 or 100%. No
`--runs` on the command line: it overrides every case's own value. A
grader that passes in some runs but not all is a decision the plugin does not pin down. Three runs were too few - a case could only
read 0, 33, 67 or 100%, and one run decided between "unstable" and "fine". Read those first — they are where a
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

## Removed cases

A case that passes every run on every model measures nothing the others do not, and costs a
run each time. Removed on 2026-10-27, both at 100% on Opus (baseline) and on Haiku (first CI
run): `language-de-request` (the German default path, which every German case walks) and
`module-source-authored` (`module_source: authored` stated in plain words). Bring one back
when a change touches what it covered.

The two draft cases `process/diagram-before-code-after-change` and `process/review-agent-separate`
were removed on 2026-10-27: both grade a step that needs a shell, which the Windows eval
sandbox does not grant, so their 0% measured the missing shell; and both steps - the diagram before code after a change,
a review agent of its own - hold reliably in the owner's own test runs. The git history has them.
