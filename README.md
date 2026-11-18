# eval-history

Data branch, no code: one entry per eval run in `index.json`, the full result under
`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),
read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;
per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the
previous version on the same model; a rate is never compared across models.

## haiku

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-haiku.json) · newest: release at `b36b7aa`, 2 run(s) per case, 2026-11-18 · Full suite on b36b7aa, before #56-#59; not repeated after them.

| Case | v0.5.2 | v0.5.3 | v0.5.4 | v0.5.5 | v0.6.0 | v0.7.0 | v0.7.2 | v0.8.0 |
|---|---|---|---|---|---|---|---|---|
| app-code-untouched |  | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| bicep-rerender-keeps-names |  |  |  | 100% | 100% | 100% | 100% | 100% |
| bicep-secret-placeholder-once | 🟡 80% | 🟡 25% ⬇ | 🟡 25% | 🟡 25% | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🟡 25% ⬆ |
| chat-rag-pattern |  |  |  |  |  |  |  | 🔴 0% |
| claude-md-section-replaced | 🟡 20% | 🟡 25% | 🟡 50% ⬆ | 🟡 50% | 🟡 75% ⬆ | 🟡 25% ⬇ | 🟡 50% ⬆ | 🟡 25% ⬇ |
| diagram-no-invented-lines | 🟡 80% | 100% ⬆ | 🟡 50% ⬇ | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🟡 50% ⬆ | 🔴 0% ⬇ |
| integration-nothing-invented |  |  |  |  |  |  |  | 🔴 0% |
| language-en-first-question | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| language-en-request | 100% | 100% | 100% | 100% | 100% | 🟡 50% ⬇ | 🟡 50% | 🔴 0% ⬇ |
| microservices-shared-environment |  |  |  |  |  |  |  | 🔴 0% |
| platform-workspace-reference |  |  |  |  |  | 🟡 25% | 🔴 0% ⬇ | 🔴 0% |
| plugin-newer-halts | 100% | 100% | 🟡 75% ⬇ | 100% ⬆ | 100% | 100% | 100% | 100% |
| requirements-stated | 🟡 20% | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% |
| terraform-code-structure |  |  |  |  |  | 🔴 0% | 🔴 0% | 🔴 0% |
| terraform-existing-reference |  |  |  |  |  | 🟡 50% | 🟡 50% | 🔴 0% ⬇ |
| trigger-workload-request | 🟡 20% | 100% ⬆ | 100% | 100% | 100% | 100% | 100% | 100% |
| vague-public-dev | 🟡 20% | 🔴 0% ⬇ | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% | 🔴 0% |
| webapp-departure-wins |  |  |  |  |  |  |  | 🔴 0% |
| **cost** | $3.20 | $0.94 | $0.82 | $0.88 | $1.04 | $2.41 | $1.53 | $1.71 |

## sonnet

![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-sonnet.json) · newest: release at `15b56ef`, 2 run(s) per case, 2026-11-18 · Composed, not one run: twelve cases from the full suite on b36b7aa (which stopped at its cost ceiling); webapp-departure-wins, vague-public-dev, platform-workspace-reference, plugin-newer-halts and trigger-workload-request from a re-test on 909e397; language-en-request from a re-test on the branch of #59. The pattern cases ran four times in the full suite, twice since #57.

| Case | v0.5.2 | v0.5.3 | v0.5.4 | v0.5.5 | v0.6.0 | v0.7.0 | v0.7.2 | v0.8.0 |
|---|---|---|---|---|---|---|---|---|
| app-code-untouched |  | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| bicep-rerender-keeps-names |  |  |  | 100% | 100% | 100% | 100% | 100% |
| bicep-secret-placeholder-once | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| chat-rag-pattern |  |  |  |  |  |  |  | 100% |
| claude-md-section-replaced | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| diagram-no-invented-lines | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| integration-nothing-invented |  |  |  |  |  |  |  | 100% |
| language-en-first-question | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| language-en-request | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| microservices-shared-environment |  |  |  |  |  |  |  | 100% |
| platform-workspace-reference |  |  |  |  |  | 100% | 100% | 100% |
| plugin-newer-halts | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| requirements-stated | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| terraform-code-structure |  |  |  |  |  | 100% | 100% | 100% |
| terraform-existing-reference |  |  |  |  |  | 100% | 100% | 100% |
| trigger-workload-request | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| vague-public-dev | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| webapp-departure-wins |  |  |  |  |  |  |  | 100% |
| **cost** | $15.62 | $14.90 | $14.56 | $18.83 | $14.80 | $22.35 | $21.03 | $44.23 |
