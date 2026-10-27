# Eval dashboard

**Status:** built (`eval-agent/dashboard`), read-only. The open questions below are answered
(2026-10-27): the runs are committed to the `eval-history` branch, a summary per run in
`index.json` (plugin version, model, trigger, pass rate per case) and the raw result beside
it; the dashboard reads `index.json` through the GitHub API without a token and compares a
run only with an older plugin version on the same model.

## Idea

A page that shows the eval runs over time: pass rates per group (`spec`, `diagram`,
`interview`, `outcome`), plugin vs. plain per case, cost per run, regressions between runs.
Fed by the eval output and, later, by the scheduled agent's verdicts.

## Open questions

- Static page (artifact) from committed result files, or a small store the runs write to?
- What is committed: raw results or a summary per run?
