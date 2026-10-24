# Spec drift check

**Status:** sketch (owner's idea, 2026-10-24, after the first full run)

## Idea

The rendered code and `infra-spec.yaml` can drift apart: someone changes a SKU in the `.tf`
without touching the spec, and the spec keeps saying P1v3 while the plan says B1. Today the
only guard is the instruction the render leaves in the repository's `CLAUDE.md` (rule 11 of
`iac-rendering`) and the tests: a `# decision:` assert fails when the code changes - but
when the assert is changed along with the code, nothing notices that the spec was not.

A drift check compares the three in one pass and reports every decision whose values
disagree:

| Source | Value |
|---|---|
| `infra-spec.yaml` | what was decided (`value`) |
| `tests/*.tftest.hcl` / `tests/*.armtest.yaml` | what the test asserts for that `# decision:` key |
| the plan (`terraform show -json` of a plan with the mocked platform, or the compiled ARM) | what the code renders |

## Output

One line per drifted decision: key, spec value, test value, planned value, and which of the
three is the odd one out - usually the spec. Exit 1 on any drift, so it can sit in the
pipeline's validate step next to `check_render_coverage.py`. A second mode proposes the spec
edit (`value`, `source: overridden`, an empty `reason` to fill in) so the fix is a review, not
archaeology.

## Open questions

- `check_render_coverage.py` already pairs decisions with asserts by key; reading the
  asserted value out of the HCL condition is the missing step (the conditions are simple
  `==` comparisons by the contract).
- Reading the planned value needs a plan: the mocked-platform plan the tests already produce,
  or `terraform show -json` on a saved plan from the pipeline.
- Bicep: the compiled ARM is the planned value; `run_arm_tests.py` already evaluates the
  asserts against it.
- Where it runs: a pre-commit hook in the customer's repository, the pipeline's validate
  step, or on request through the plugin.
