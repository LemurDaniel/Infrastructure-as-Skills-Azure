# Draft eval cases

Not loaded by `claude plugin eval`, which reads `evals/**/case.yaml` only. A case is here when it
cannot measure the plugin where the suite runs today: both cases below grade a step that needs a
shell (the diagram script, the review of the picture it draws), and the eval sandbox on Windows
grants none. Without one, the first Sonnet runs scored 0% on both because the picture could not
exist, not because the plugin skipped it.

| Case | Needs |
|---|---|
| `process/diagram-before-code-after-change` | the diagram drawn before code after a change of the spec |
| `process/review-agent-separate` | a drawn picture for a review agent of its own to look at |

To bring one back: move it to `evals/<group>/`, add `Bash` to `allowed_tools` in its `prompt.md`,
and run the suite on Linux with `--allow-tools Write Edit Bash` (the Windows sandbox refuses a case
that grants a shell).
