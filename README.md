# eval-history

Data branch, no code: one entry per eval run in `index.json`, the full result under
`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),
read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;
per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the
previous version on the same model; a rate is never compared across models.

## haiku

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-haiku.json) · newest: pr, 3 run(s) per case, 2026-10-27

| Case | v0.5.2 |
|---|---|
| diagram-no-invented-lines | 🟡 67% |
| language-en-request | 100% |
| requirements-stated | 🔴 0% |
| trigger-workload-request | 🟡 33% |
| vague-public-dev | 🔴 0% |
| **cost** | $0.84 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: manual, 3 run(s) per case, 2026-10-27 · composite: 6 cases from the 02:42 run, 3 re-tested at 02:58 after f338a96; drafts excluded

| Case | v0.5.2 |
|---|---|
| bicep-secret-placeholder-once | 🟡 67% |
| claude-md-section-replaced | 🟡 67% |
| diagram-no-invented-lines | 🟡 67% |
| language-en-first-question | 🟡 67% |
| language-en-request | 100% |
| plugin-newer-halts | 100% |
| requirements-stated | 100% |
| trigger-workload-request | 100% |
| vague-public-dev | 100% |
| **cost** | $14.25 |
