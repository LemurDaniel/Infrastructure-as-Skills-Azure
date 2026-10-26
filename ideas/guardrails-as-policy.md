# Guardrails as policy

**Status:** sketch - larger project, not a first step

## Idea

The guardrails that hold for every resource (no public network access, no shared keys, TLS
minimum, encryption) are also emitted as Azure Policy definitions and/or Checkov rules. The
plugin renders code that follows them; the policy enforces them on code nobody generated
with the plugin - hand-written Terraform, the portal, another team.

One source: the question set's decision and its security-shaped default produce the rule, so
generation and enforcement cannot drift apart.

## Open questions

- Which guardrails map cleanly to a policy (many are property checks) and which do not.
- Policy at deploy time (Azure Policy, deny/audit) vs. at PR time (Checkov in the pipeline),
  or both.
- Ownership: policy is usually a platform concern, outside what this plugin owns
  (`resolved_by: derived`).
