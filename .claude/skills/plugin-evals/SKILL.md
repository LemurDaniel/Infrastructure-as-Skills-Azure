---
name: plugin-evals
description: Writing, running and reading the plugin's eval suite (claude plugin eval, plugins/infrastructure-as-skills-azure/evals/). Use when adding or changing an eval case or grader, running the suite, interpreting results, or after a bug found in a real run should become a regression case. Triggers on "eval", "evals", "testcase", "Testfall", "grader", "plugin eval", "Regression", "wie gut ist der Output".
---

# Plugin evals — Infrastructure-as-Skills-Azure

The suite lives in `plugins/infrastructure-as-skills-azure/evals/`, one directory per case, and
runs with `claude plugin eval`. Its [README](../../../plugins/infrastructure-as-skills-azure/evals/README.md)
holds the case matrix and the method; this file holds how to work on it without repeating
the mistakes already made once.

## 1. What a case is here

A request goes in; the plugin interviews, writes `infra/infra-spec.yaml` and
`infra/naming.yaml`; the graders read the spec. The spec is the artefact this plugin exists
to get right, so it is what gets graded — not the chat.

```
evals/<case>/
  prompt.md     # frontmatter: description, expected_outcome, tags, runs, limits, allowed_tools
  case.yaml     # schema_version "1.1", name, graders:
```

Every prompt is written the way a real user would write it, in German, and ends with the
same paragraph — because a run is headless and nobody answers follow-up questions:

```
Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
```

Keep that paragraph identical across cases. A case that differs in its harness
instructions measures the instructions, not the plugin.

## 2. Hard constraints of the harness

Each of these cost a run to discover.

- **No shell on Windows.** A case that lists `Bash` or `PowerShell` in `allowed_tools` is
  refused before it starts: the eval sandbox has no Windows backend, and the run fails
  closed. So `check_spec.py`, `new_diagram.py` and the draw.io export cannot run inside a
  case here. Cases list `[Read, Glob, Grep, Skill, Write, Edit]`; run `check_spec.py`
  yourself on the produced specs afterwards (section 4). Shell-dependent graders come back
  only on a Linux runner with bubblewrap.
- **Write tools must be in the case, not only on the command line.** A grader that reads a
  file the run creates is flagged "cannot pass" unless the case's `allowed_tools` includes
  `Write`/`Edit` *and* the run grants them with `--allow-tools Write Edit`.
- **`plugins: ["../.."]`** in every `prompt.md` (`"../../.."` from `evals/<group>/<case>/`) — the path from the case directory to the
  plugin. Without it the plugin may not resolve and the run has no with-arm.
- **The workspace starts empty.** No IaC root, so the spec lands in `infra/` — which is
  why every path grader says `infra/...`. A case that needs an existing repository (an
  extension run) needs a `context.scaffold_script` and `--scaffold`.
- **No custom-code graders.** `regex`, `tool_used`, `tool_order`, `file_exists`, `llm`,
  `baseline` — nothing else.
- **`file_exists` sees only files created during the run**, not files the scaffold made.

## 3. Writing graders

**Regex over the spec file first.** It reads the whole file identically every run, costs
nothing, and a failure names the decision. The same decision comes out in several shapes —
inline (`key: { value: x }`), as a block (`key:` then `value: x` indented on the next
line), a bare value, and with comment lines between key and value. Agents add those
comments freely. Use this shape for every "key has value" check:

```yaml
- name: exposure-private
  type: regex
  weight: 2
  target: { source: file, path: infra/infra-spec.yaml }
  pattern: 'network_exposure:\s*(?:#[^\n]*\s*)*(?:\{\s*)?(?:value:\s*)?\W?private\b'
```

Never a fixed-width gap like `\W{0,3}` or `[\s\S]{0,60}`: the first three-run measurement
reported four graders as UNSTABLE, and all four were a correct spec in block form or with
a comment — grader failures that read like plugin failures.

- A resource the run must **not** create: `'^\s{2}virtual-network:'` with `flags: m` and
  `match: not_contains` — two spaces is a key directly under `resources:`.
- A value the run must **not invent** — subscription GUID, `value:\W{0,3}rg-`, an address
  range nobody stated. Weight these up (2–3): they are the failures that look plausible and
  surface only at apply time.
- An open item: `'^open:[\s\S]*resource_group_name'` with `flags: m`.
- Exactly N resources: `match: 'count:3'`.
- JavaScript regex: `flags: i` for case-insensitivity; inline `(?i)` is not supported.

Test every new pattern against a real spec before running the suite — a regex that never
matches the YAML's actual shape fails every run and says nothing about the plugin:

```powershell
python -I -c "import re,sys; s=open(sys.argv[1],encoding='utf-8').read(); print(bool(re.search(sys.argv[2], s, re.M)))" <spec> '<pattern>'
```

**Per case, one grader on the process:** `tool_used` on `Skill` with
`input_match: iac-authoring`. It is an indicator, excluded from the score against the
no-plugin arm.

**An `llm` grader only for short output** — the final message — with concrete PASS and
FAIL conditions and "language and formatting do not matter". Never an `llm` grader over
the spec; that is what the regexes are for. Before trusting a new judge, compare its
verdicts with your own on a few runs, passes and fails separately.

## 4. Running

Check that the cases load, without spending anything — the cost ceiling is checked before
each run, so `0` loads and validates every case and starts none:

```powershell
$claude = (Get-Item "$HOME/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude.exe" | Select-Object -Last 1).FullName
& $claude plugin eval plugins/infrastructure-as-skills-azure --trust-plugin --no-publish --max-cost-usd 0 --runs 1 --ablation none --allow-tools Write Edit
```

`--case` filters *before* loading, so it cannot be used for this.

A first look — one run per case, no baseline arm, in parallel:

```powershell
& $claude plugin eval plugins/infrastructure-as-skills-azure --trust-plugin --no-publish --runs 1 --ablation none -j 3 --allow-tools Write Edit --keep-temp --json <scratch>/eval.json
```

The full measurement is the default: 3 runs per case and the no-plugin arm, so
3 cases × 3 runs × 2 arms = 18 agent runs. Start it in the background and say what it
costs before starting it.

Afterwards:

```powershell
python3 .claude/skills/plugin-evals/scripts/show_eval_result.py <scratch>/eval.json
```

It lists failing graders with their explanation, flags a grader that passed in some runs
but not all as **UNSTABLE**, and reports a run that never started as a harness error
rather than as fifteen grader failures.

It also compares every grader against **`evals/baseline.json`** — the committed snapshot
of the last accepted run, passed-of-total per case and grader — and marks a lower rate
as **REGRESS** (exit 1, even when every case still passes on aggregate). That is the
memory between runs: without it, a decision that went from 3/3 to 2/3 looks like a case
that still passes. After reading a run and accepting it:

```powershell
python3 .claude/skills/plugin-evals/scripts/show_eval_result.py <scratch>/eval.json --update-baseline
```

and commit `baseline.json` with the change it measures.

When a failure is fixed, add an entry to `evals/LEARNINGS.md` first — case, symptom, cause,
fix, rate after — and commit it with the fix. The baseline says that a rate dropped;
the entry says why, including a grader that was wrong rather than the output. Never update it from a run you
have not read — a bad run written into the baseline hides the regression it carries. A run
with a harness error is refused as a baseline.

Then validate the produced specs yourself, since the case cannot:

```powershell
python3 plugins/infrastructure-as-skills-azure/core/iac-authoring/scripts/check_spec.py <kept workspace>/infra/infra-spec.yaml
```

`--keep-temp` keeps each run's directory under `%TEMP%\claude-eval-*`. Everything in it
except `out/` and `config/` may be agent-written: read files, never run git or anything that
loads configuration from inside it, and remove the directories when done — the run prints
the exact `Remove-Item` line.

**In CI** `.github/workflows/plugin-evals.yml` runs the suite on a pull request on Haiku,
three runs per case in parallel, one case per call with progress in the log, report only,
with one pull request comment updated per push, and `record_eval_history.py` writes the run to the
`eval-history` branch (version, model, trigger, pass rates; the full result beside it). A
Haiku rate is never compared with a baseline taken on another model, and never accepted
into `baseline.json`.

## 5. Reading results

The method is in the README (Hamel Husain's critique shadowing). In practice:

1. **Harness errors first.** `turns: 0` means nothing was tested. Fix the case or the
   flags, not the plugin.
2. **Read the failing specs before touching a grader.** A grader is wrong only when the
   spec is right and the regex missed it; then fix the pattern and test it against that
   spec.
3. **UNSTABLE is the most valuable signal.** A decision that comes out differently in runs
   of the same prompt is one the plugin leaves to chance — a missing default, an ambiguous
   rule in `iac-authoring`, a Phase 0 mapping that guesses. The fix goes into the plugin.
4. **Group failures by cause and fix the most frequent first.**
5. **A fixed failure becomes a case or a grader**, so it stays fixed.

## 6. Adding a case

Pick a combination the README's matrix does not cover yet, write the prompt as a user
would, then:

- one grader per decision the prompt settles,
- one per value the plugin must not invent, weighted up,
- the `Skill` indicator and `no-code-before-confirmation`,
- load-check it at `--max-cost-usd 0`, test each regex against a real spec,
- add the row to the README's matrix.

Results go to `evals/results/`, which is ignored. Commit cases, never results.
