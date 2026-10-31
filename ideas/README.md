# Ideas

There is no roadmap; this is the direction, one file per idea: what it is, why it might be
worth it, a first sketch, open questions. Nothing here is built or promised. When an idea is
taken up, `PROGRESS.md` records the decision and its file gets a pointer to it.

| Idea | Status |
|---|---|
| [Pattern skill](pattern-skill.md) - whole systems, the wiring owned, requirements choose the pattern | Sketch, the largest open piece |
| [Quality gates](quality-gates.md) - PSRule, cross-backend diff, CI in this repo, a consistency number | Sketch |
| [Autonomous Terraform agent](autonomous-terraform-agent.md) - scheduled, tests on a real subscription, opens PRs | Sketch |
| [AVM drift watch](avm-drift-watch.md) - light first step, bumps pins via PR | Sketch |
| [Review agent](review-agent.md) - existing infra vs. guardrails | Sketch |
| [Cost estimate and profiles](cost-and-security-profiles.md) - a monthly estimate per stage in Phase 4; the profiles exist as `priority` | Sketch, the estimate is open |
| [Eval dashboard](eval-dashboard.md) - runs over time | Sketch |
| [Eval agent](eval-agent.md) - runs the evals on request, files tickets per cause | Agent superseded by `eval.plugin.yaml` + `eval-history`; dashboard read-only |
| [Diagram fuzz](diagram-fuzz.md) - random specs drawn and scored on layout, on CI and on the eval agent | Sketch, fuzzer exists |
| [Simulated customer in the evals](simulated-customer-eval.md) - scripted answers so the interview path runs | Sketch |
| [Spec versions and diff](spec-diff.md) - readable "what changed" between two specs | Sketch |
| [Spec drift check](spec-drift-check.md) - spec vs. tests vs. plan, every decision whose values disagree | Sketch |
| [Guardrails as policy](guardrails-as-policy.md) - same rules enforced as Azure Policy / Checkov | Sketch, large |
| [Question-set generator](question-set-generator.md) - drafts new families | Sketch |
