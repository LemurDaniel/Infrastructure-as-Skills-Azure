# eval-history

Data branch, no code: one entry per eval run in `index.json`, the full result under
`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),
read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;
per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the
previous version on the same model; a rate is never compared across models.

## haiku

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-haiku.json) · newest: manual, 5 run(s) per case, 2026-10-27 · newest run per case: full run 03:06, re-tests after cd5523b; bicep re-graded after 6f280d0

| Case | v0.5.2 |
|---|---|
| bicep-secret-placeholder-once | 🟡 20% |
| claude-md-section-replaced | 🔴 0% |
| diagram-no-invented-lines | 100% |
| language-en-first-question | 100% |
| language-en-request | 100% |
| plugin-newer-halts | 100% |
| requirements-stated | 🟡 20% |
| trigger-workload-request | 🟡 40% |
| vague-public-dev | 🟡 20% |
| **cost** | $2.20 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: manual, 5 run(s) per case, 2026-10-27 · newest run per case: full run 02:42, re-tests after f338a96, 726c9a9, cd5523b; bicep re-graded after 6f280d0

| Case | v0.5.2 |
|---|---|
| bicep-secret-placeholder-once | 🟡 80% |
| claude-md-section-replaced | 100% |
| diagram-no-invented-lines | 🟡 67% |
| language-en-first-question | 🟡 67% |
| language-en-request | 100% |
| plugin-newer-halts | 100% |
| requirements-stated | 100% |
| trigger-workload-request | 100% |
| vague-public-dev | 100% |
| **cost** | $15.88 |
