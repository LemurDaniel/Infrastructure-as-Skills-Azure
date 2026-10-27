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

## opus

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-opus.json) · newest: baseline, 3 run(s) per case, 2026-10-25

| Case | v0.0.2 |
|---|---|
| claude-md-section-replaced | 100% |
| diagram-before-code-after-change | 🔴 0% |
| diagram-no-invented-lines | 100% |
| language-de-request | 100% |
| language-en-first-question | 100% |
| language-en-request | 100% |
| module-source-authored | 100% |
| plugin-newer-halts | 100% |
| requirements-stated | 100% |
| trigger-workload-request | 100% |
| vague-public-dev | 100% |
| **cost** | $0.00 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: manual, 3 run(s) per case, 2026-10-27

| Case | v0.5.2 |
|---|---|
| bicep-secret-placeholder-once | 🟡 67% |
| claude-md-section-replaced | 🟡 33% |
| diagram-before-code-after-change | 🔴 0% |
| diagram-no-invented-lines | 🟡 67% |
| language-en-first-question | 🟡 67% |
| language-en-request | 100% |
| plugin-newer-halts | 100% |
| requirements-stated | 🟡 67% |
| review-agent-separate | 🔴 0% |
| trigger-workload-request | 100% |
| vague-public-dev | 🟡 67% |
| **cost** | $18.03 |
