# eval-history

Data branch, no code: one entry per eval run in `index.json`, the full result under
`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),
read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;
per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the
previous version on the same model; a rate is never compared across models.

## haiku

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-haiku.json) · newest: release at `82ea823`, 2 run(s) per case, 2026-10-27 · Full suite, effort low, each case's own runs, judge sonnet, before the 0.5.3 merge

| Case | v0.5.2 | v0.5.3 |
|---|---|---|
| app-code-untouched |  | 100% |
| bicep-secret-placeholder-once | 🟡 80% | 🟡 25% ⬇ |
| claude-md-section-replaced | 🟡 20% | 🟡 25% |
| diagram-no-invented-lines | 🟡 80% | 100% ⬆ |
| language-en-first-question | 100% | 100% |
| language-en-request | 100% | 100% |
| plugin-newer-halts | 100% | 100% |
| requirements-stated | 🟡 20% | 🔴 0% ⬇ |
| trigger-workload-request | 🟡 20% | 100% ⬆ |
| vague-public-dev | 🟡 20% | 🔴 0% ⬇ |
| **cost** | $3.20 | $0.94 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: release at `82ea823`, 2 run(s) per case, 2026-10-27 · Full suite, effort low, each case's own runs (4, the four costliest 2), before the 0.5.3 merge

| Case | v0.5.2 | v0.5.3 |
|---|---|---|
| app-code-untouched |  | 100% |
| bicep-secret-placeholder-once | 100% | 100% |
| claude-md-section-replaced | 100% | 100% |
| diagram-no-invented-lines | 100% | 100% |
| language-en-first-question | 100% | 100% |
| language-en-request | 100% | 100% |
| plugin-newer-halts | 100% | 100% |
| requirements-stated | 100% | 100% |
| trigger-workload-request | 100% | 100% |
| vague-public-dev | 100% | 100% |
| **cost** | $15.62 | $14.90 |
