# eval-history

Data branch, no code: one entry per eval run in `index.json`, the full result under
`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),
read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;
per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the
previous version on the same model; a rate is never compared across models.

## haiku

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-haiku.json) · newest: release at `519fad2`, 2 run(s) per case, 2026-11-01 · Composed: full suite on a4cf3c2; both terraform-* cases re-tested on 7fbbcb6 (#26, graders read file contents); terraform-code-structure not re-run after #27. Release PR #21.

| Case | v0.5.2 | v0.5.3 | v0.5.4 | v0.5.5 | v0.6.0 | v0.7.0 |
|---|---|---|---|---|---|---|
| app-code-untouched |  | 100% | 100% | 100% | 100% | 100% |
| bicep-rerender-keeps-names |  |  |  | 100% | 100% | 100% |
| bicep-secret-placeholder-once | 🟡 80% | 🟡 25% ⬇ | 🟡 25% | 🟡 25% | 🔴 0% ⬇ | 🔴 0% |
| claude-md-section-replaced | 🟡 20% | 🟡 25% | 🟡 50% ⬆ | 🟡 50% | 🟡 75% ⬆ | 🟡 25% ⬇ |
| diagram-no-invented-lines | 🟡 80% | 100% ⬆ | 🟡 50% ⬇ | 🔴 0% ⬇ | 🔴 0% | 🔴 0% |
| language-en-first-question | 100% | 100% | 100% | 100% | 100% | 100% |
| language-en-request | 100% | 100% | 100% | 100% | 100% | 🟡 50% ⬇ |
| platform-workspace-reference |  |  |  |  |  | 🟡 25% |
| plugin-newer-halts | 100% | 100% | 🟡 75% ⬇ | 100% ⬆ | 100% | 100% |
| requirements-stated | 🟡 20% | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% |
| terraform-code-structure |  |  |  |  |  | 🔴 0% |
| terraform-existing-reference |  |  |  |  |  | 🟡 50% |
| trigger-workload-request | 🟡 20% | 100% ⬆ | 100% | 100% | 100% | 100% |
| vague-public-dev | 🟡 20% | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% |
| **cost** | $3.20 | $0.94 | $0.82 | $0.88 | $1.04 | $2.41 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: release at `519fad2`, 2 run(s) per case, 2026-11-01 · Composed: full suite on a4cf3c2; terraform-existing-reference re-tested on 7fbbcb6 (#26, graders read file contents); terraform-code-structure re-tested on 519fad2 (#27). Release PR #21.

| Case | v0.5.2 | v0.5.3 | v0.5.4 | v0.5.5 | v0.6.0 | v0.7.0 |
|---|---|---|---|---|---|---|
| app-code-untouched |  | 100% | 100% | 100% | 100% | 100% |
| bicep-rerender-keeps-names |  |  |  | 100% | 100% | 100% |
| bicep-secret-placeholder-once | 100% | 100% | 100% | 100% | 100% | 100% |
| claude-md-section-replaced | 100% | 100% | 100% | 100% | 100% | 100% |
| diagram-no-invented-lines | 100% | 100% | 100% | 100% | 100% | 100% |
| language-en-first-question | 100% | 100% | 100% | 100% | 100% | 100% |
| language-en-request | 100% | 100% | 100% | 100% | 100% | 100% |
| platform-workspace-reference |  |  |  |  |  | 100% |
| plugin-newer-halts | 100% | 100% | 100% | 100% | 100% | 100% |
| requirements-stated | 100% | 100% | 100% | 100% | 100% | 100% |
| terraform-code-structure |  |  |  |  |  | 100% |
| terraform-existing-reference |  |  |  |  |  | 100% |
| trigger-workload-request | 100% | 100% | 100% | 100% | 100% | 100% |
| vague-public-dev | 100% | 100% | 100% | 100% | 100% | 100% |
| **cost** | $15.62 | $14.90 | $14.56 | $18.83 | $14.80 | $22.35 |
