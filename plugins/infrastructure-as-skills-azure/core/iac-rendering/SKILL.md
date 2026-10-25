---
name: iac-rendering
description: Turns an infra-spec.yaml into Terraform or Bicep — file and module layout, variables, naming, tagging, tests. Read when rendering a spec, when porting a configuration between the two targets, or when reviewing generated code for idiom.
---

# Rendering a spec

This skill is the second half of the pipeline:

```
question set  ──interview──>  infra-spec.yaml  ──render──>  Terraform / Bicep
              [iac-authoring]                  [here]
```

The split is the point. The interview resolves decisions and writes them in a
backend-neutral vocabulary; this layer is the only one allowed to know that
`public_network_access: disabled` is `public_network_access_enabled = false` in one target
and `properties.publicNetworkAccess: 'Disabled'` in the other. Merge the two and the
vocabulary leaks within a week.

So: **never render without a spec.** If there is none, go to
[iac-authoring](../iac-authoring/SKILL.md) and write one first. Rendering straight from a
conversation produces code nobody can regenerate and a decision record that does not exist.

## What the spec hands over

| Spec | What this layer does with it |
|---|---|
| `spec.target` | Picks Terraform or Bicep. Never both from one run |
| `composition` | The module split. One `modules` entry is a directory (Terraform) or a file (Bicep) |
| `context` | Variables/parameters shared by every module, resolved once |
| `resources.<id>` | Decisions → attributes, via the question set's `renders` and the resource's own rendering reference |
| `wiring` | Renders into the root, never into a module — only the caller sees both ends |
| `_target_overrides` | Target-specific escape hatches, each with its comment |

The schema is in
[../iac-authoring/references/spec.md](../iac-authoring/references/spec.md). Read it rather
than inferring the shape from an example spec.

## Order of work

1. **Match the repository before the defaults.** An existing layout, module granularity or
   API version wins over anything in the references here. Generated code that does not look
   like its neighbours gets rewritten by hand, and then the spec is stale.
2. **Resolve the Azure Verified Module for each resource** — [avm.md](references/avm.md).
   AVM is the primary rendering target: a resource with an `Available` module renders as a
   call to it, with every decision written out as an input; a resource without one renders
   authored, and the spec records `implementation: authored` with the reason. The module
   version is looked up live and pinned in the code, never recalled. Skip only when the
   spec's `deployment.module_source` is `authored` or the repository already renders the
   resource authored.
3. **Read the target idiom** — [terraform-idiom](references/terraform-idiom.md) or
   [bicep-idiom](references/bicep-idiom.md), not both.
4. **Read the resource's own rendering reference**, `resources/<family>/<resource>/{terraform,bicep}.md`.
   It opens with the decision → module input mapping and the rendered call, and holds
   what the spec cannot: which decisions are fixed at creation, which the module does not
   expose, the shape differences between the two targets. The authored rendering follows
   it, for the fallback case and for reading what the module does inside.
5. **Render names from the right mechanism** — [naming.md](references/naming.md). The
   Terraform provider resolves them; in Bicep they are assembled from vars because the
   naming modules are not shipped.
6. **Write the secure value explicitly**, even where it matches the provider or API
   default. A default can move between versions and an absent attribute is invisible in
   review.
7. **Render the tests with the code, not after it.** Every decision under `resources:`
   in the spec is asserted by exactly one test, and a decision that cannot be observed in
   a plan is marked as such with its reason. A render without its tests is not finished —
   the tests are what make "the code matches the spec" a check instead of a claim, and
   what makes the next re-render a diff instead of a review. The shape per target is in
   the idiom file; `scripts/check_render_coverage.py` fails on an unasserted decision.
8. **Validate before handing over.** Syntactically valid is not done — `fmt` →
   `validate` → `test` → `plan` / `what-if`, then say which diffs are service-affecting.
   The commands are at the end of each idiom file. **Then show the names**: run
   `scripts/list_names.py <spec>` and hand over the table - every resource with the name it
   will get, before anything is deployed. A name cannot be changed afterwards, and the
   customer knows whether it fits. It works from the spec alone: no tool or login is
   assumed, and no plan is read. What it cannot know is in
   [naming.md](references/naming.md#names-before-the-deploy).
9. **The diagram is the customer's; a render does not touch it.** They signed off on
   `infra-diagram.drawio.png` before this render started (iac-authoring Phase 5), and the
   code is rendered from the same spec the picture was drawn from, so the picture stays as
   agreed. A render never redraws it. The only thing that changes the picture is a change
   to the spec, and that is not the renderer's to make: a finding whose cause is the spec
   goes back to Phase 5, where the spec is corrected, the diagram redrawn
   ([iac-diagram](../iac-diagram/SKILL.md)) and the customer asked again before the render
   continues.
10. **Render the pipeline the spec chose.** `deployment.deploy_mechanism` names the system
    (`github`, `azure_devops`, `gitlab`, `local`); the stages, the approval gate and the
    login come from the same spec as the code. Read [pipelines.md](references/pipelines.md),
    then that system's file, and hand over the platform prerequisites it lists - a pipeline
    that cannot run until an identity and its environments exist must say so. Run
    `scripts/check_pipeline.py <spec>` before handing over; it fails on a missing stage, a
    gate that does not match `pipeline_approvals`, an apply without a saved plan and a
    secret in the file.
11. **Write or update the repository's `CLAUDE.md`, so the spec does not drift.** The
    rendered code will be edited by people and by Claude long after this run - a SKU
    bumped, a retention changed - and every such edit that is not mirrored into
    `infra-spec.yaml` turns the spec into a record of what was once decided. So the render
    leaves an instruction behind in the repository root: create `CLAUDE.md` if there is
    none, else add or replace **only** the section between the two markers below, never
    the rest of the file (it is the customer's). The section names the spec as the source
    of truth, the rule that a change to the code is a change to the spec first (the value,
    `source: overridden`, a `reason`), what is regenerated from it (decision document,
    diagram, tests) and the checks that prove the two still agree.

    ```markdown
    <!-- infrastructure-as-skills: begin - regenerated by the plugin, edit outside the markers -->
    ## Infrastructure: the spec is the source of truth

    `<root>/infra-spec.yaml` records every infrastructure decision with where it came from;
    the Terraform/Bicep under `<root>/` is rendered from it, so are `infra-decisions.md`,
    `infra-diagram.drawio.png` and the tests.

    - **A change to the infrastructure is a change to the spec first.** Changing a SKU, a
      retention, an access rule in the code alone makes the spec lie. Set the decision's
      `value` in the spec, mark it `source: overridden` with a one-line `reason`, then change
      the code and its `# decision:` test the same way - or re-render from the spec with the
      plugin's `azure-resources` skill, which asks nothing it already knows.
    - **A new resource or a removed one goes through the interview**, not through a new
      `.tf`/`.bicep` file: the spec gains or loses the resource, and the render follows.
    - **Start every infrastructure change with the plugin's `iac-authoring` skill**, even
      when the request names no Azure term ("make it private", "bigger plan"): it finds
      this spec and extends it, asking only the delta.
    - **Resource groups are the destructive edit.** Switching a group between `existing`
      and `create`, or moving a resource to another group role, creates, destroys or moves
      real resources. Read the plan (what-if) before applying, say so in the hand-over, and
      never apply a plan that destroys a group; the production lock blocks that on purpose.
    - **The order is fixed, also for a direct edit of the spec:** spec, `check_spec.py`,
      redraw the diagram (`iac-diagram`), sign-off, only then code and tests. A spec change
      without the redrawn diagram is unfinished; never start the Bicep/Terraform before it.
    - **After every change run**, in `<root>/`: `check_spec.py infra-spec.yaml`,
      `terraform test` (or `run_arm_tests.py infra-spec.yaml` for Bicep) and
      `check_render_coverage.py infra-spec.yaml` from the plugin's
      `core/iac-authoring/scripts/` and `core/iac-rendering/scripts/`; a decision the tests
      no longer assert, or assert with another value than the spec, is drift.
    - `infra-decisions.md` and `infra-diagram.drawio.png` are regenerated from the spec
      (`export_decisions.py`, `iac-diagram`); do not edit them by hand - a diagram the
      customer changed is a question for the spec.
    <!-- infrastructure-as-skills: end -->
    ```

    `<root>` is the IaC root relative to the repository root (`infra/`, or `.`). Say in
    the hand-over that the file was written or which section was replaced.
12. **Run it the way Phase 5 settled.** The working mode - **Subagents** or **Same
    session** - was asked once at the start of `iac-authoring` Phase 5, before the diagram
    loop, and holds for this loop too; ask it here only when this render starts in a run
    that never went through Phase 5 (a carried spec rendered on its own), with the Agent
    tool available and several resource families. Subagents run the code loop - code,
    pipeline and a read-only test agent, with a bounded fix loop - after the diagram loop
    has ended with the customer's yes; never both at once. The protocol, the stop rules and
    what goes into an agent's brief are in [agents.md](references/agents.md). Same session
    does the steps above in order, itself. The answer is a working mode, not a decision: it
    is not written to the spec. A small spec, or a host without the Agent tool, is not
    asked - it is rendered in sequence.

## Do not invent attributes

A plausible-looking argument that does not exist is worse than asking. Provider schemas
move, and exact spellings are not something to recall from memory.

- **Terraform** — `terraform providers schema -json` in the target directory (needs
  `terraform init`). Narrow it with `jq`; it is megabytes.
- **Bicep** — compile early: `bicep build --stdout <file>` fails loudly on an unknown
  property. For API versions, prefer the one already used in the repository.

When neither is available, name the attribute you are unsure about instead of guessing. A
named uncertainty is cheap to resolve; a wrong argument found at apply time is not.

## Porting between the two targets

A spec rendered twice should differ only where the platforms genuinely differ. The
asymmetries that do not survive a naive port are called out in each idiom file — module
scope versus provider aliases, deployment names, where soft delete lives, how replication
is spelled. A port that reads as a transliteration has usually lost one of them.

## Reference files

| File | When |
|---|---|
| [references/avm.md](references/avm.md) | Always, before the idiom: which module, which version, the shared interfaces, the test contract with a module in the middle |
| [references/naming.md](references/naming.md) | Always, before rendering a name |
| [references/terraform-idiom.md](references/terraform-idiom.md) | Target is Terraform |
| [references/bicep-idiom.md](references/bicep-idiom.md) | Target is Bicep |
| [references/pipelines.md](references/pipelines.md) | Always, after the code: the flow and invariants every pipeline shares |
| [references/pipelines.github.md](references/pipelines.github.md), [.ado.md](references/pipelines.ado.md), [.gitlab.md](references/pipelines.gitlab.md), [.local.md](references/pipelines.local.md) | `deploy_mechanism` is that system |
| [references/agents.md](references/agents.md) | The Agent tool is available and the spec spans several families: the two loops in sequence, the stop rules, the briefs |
| [../iac-authoring/references/spec.md](../iac-authoring/references/spec.md) | Reading the spec you render from |
| [../iac-authoring/references/guardrails.md](../iac-authoring/references/guardrails.md) | A value in the spec looks wrong and you need the rule behind it |
| `scripts/run_arm_tests.py` | A Bicep render: its `tests/*.armtest.yaml` against the compiled ARM |
| `scripts/check_pipeline.py` | After rendering a pipeline: the invariants of `pipelines.md`, per platform |
| `scripts/list_names.py` | After rendering: the names every resource will get, offline from the spec; fails on a length, a character or a duplicate |
| `scripts/check_render_coverage.py` | After rendering, either target: every spec decision asserted or marked, nothing stale |
