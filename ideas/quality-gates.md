# Quality gates

**Status:** sketch

## Idea

The plugin's quality is asserted by its own checks. Four gates would make it shown rather
than claimed, each independent of the guardrails the plugin wrote itself:

1. **PSRule for Azure** on every render: Bicep directly, Terraform through the plan JSON.
   Microsoft's rule set for the Well-Architected Framework judges the output without
   knowing this plugin. Where a guardrail and a rule disagree, the disagreement is
   documented, never suppressed. A pipeline gate on the runner (`microsoft/ps-rule`), not a
   step on the customer's machine; the plugin stays Markdown, YAML and Python.
2. **The cross-backend diff automated:** one spec rendered to both targets, both renders
   normalised to the decision level, failing on any difference not listed as a known
   asymmetry in the idiom files. The first manual diff found a real divergence (private
   endpoint naming); the sets added since have no Bicep render at all.
3. **GitHub Actions in this repository:** the consistency script, `check_spec`,
   `check_question_set`, `terraform test` on the examples, `bicep build` and `lint`, render
   coverage, the pipeline tests, PSRule, the eval suite against its baseline. Nothing merges
   red. Today the only workflow is `release.yml`.
4. **A consistency number:** the same request five times, the spread of the decisions
   measured and published in the README. The eval runs give the material; the measure is
   not defined yet.

## Open questions

- PSRule on a Terraform plan needs a plan, and a plan needs credentials or a complete mock;
  the examples only mock. Either the gate runs on the sandbox subscription or only on Bicep.
- The eval suite costs about $5 per full run; on every pull request that adds up. A nightly
  run against the baseline, and per pull request only the cheap checks.
- The consistency number depends on the model and changes with it; publish it with the
  model and the date, like the AVM version tables.
